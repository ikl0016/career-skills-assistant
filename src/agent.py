import json, os, re, time
from dotenv import load_dotenv
from openai import OpenAI, BadRequestError
from pydantic import ValidationError
from tools import ToolBox, TOOL_SCHEMAS
from prompts import SYSTEM_PROMPT
from validate import parse, semantic_errors

load_dotenv()
client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])
MODEL = os.environ["LLM_MODEL"]

YES = re.compile(r"^\s*(yes|y|yeah|yep|sure|confirm|please do)\b", re.I)

def is_yes(text):
    return bool(YES.match(text))

class Session:
    """One conversation for one signed-in employee."""

    def __init__(self, employee_id):
        self.tools = ToolBox(employee_id)
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.log = []      # latency + tokens for every model call
        self.trace = []    # tool calls made during the current question

    def _call_model(self, tool_choice="auto"):
        """tool_choice="none" forces a text answer: the model cannot call tools."""
        t0 = time.perf_counter()
        for attempt in range(2):          # retry once on a malformed tool call
            try:
                resp = client.chat.completions.create(
                    model=MODEL, messages=self.messages, tools=TOOL_SCHEMAS,
                    tool_choice=tool_choice, temperature=0)
                break
            except BadRequestError:
                if attempt == 1:
                    raise
        self.log.append({"ms": round((time.perf_counter() - t0) * 1000),
                         "tokens": resp.usage.total_tokens if resp.usage else None})
        return resp.choices[0].message

    def ask(self, user_text, max_steps=10):
        # Consent is decided by CODE from the human's words, never by the model.
        self.tools.user_confirmed = is_yes(user_text) and self.tools.pending_course is not None
        self.trace = []
        self.messages.append({"role": "user", "content": user_text})

        for _ in range(max_steps):
            msg = self._call_model()
            if not msg.tool_calls:                       # model is done -> final answer
                self.messages.append({"role": "assistant", "content": msg.content or ""})
                return self._finalize(msg.content or "")

            self.messages.append({"role": "assistant", "content": msg.content or "",
                "tool_calls": [{"id": c.id, "type": "function",
                                "function": {"name": c.function.name,
                                             "arguments": c.function.arguments}}
                               for c in msg.tool_calls]})
            for call in msg.tool_calls:                  # run each requested tool
                try:
                    args = json.loads(call.function.arguments or "{}")
                    result = self.tools.dispatch(call.function.name, args)
                except json.JSONDecodeError:
                    args, result = {}, {"error": "arguments were not valid JSON"}
                self.trace.append({"tool": call.function.name, "args": args})
                self.messages.append({"role": "tool", "tool_call_id": call.id,
                                      "content": json.dumps(result)})

        # Step limit reached: don't give up -- force a final answer with no more tools.
        self.messages.append({"role": "user", "content":
            "You have enough information. Do not call any more tools. "
            "Reply now with your final answer as ONE JSON object."})
        msg = self._call_model(tool_choice="none")
        raw = msg.content or ""
        self.messages.append({"role": "assistant", "content": raw})
        return self._finalize(raw)

    def _finalize(self, raw):
        for attempt in range(2):
            try:
                reply = parse(raw)
                errs = semantic_errors(reply, self.tools)
                if not errs:
                    recs = reply.recommendations.model_dump() if reply.recommendations else None
                    return {"message": reply.message, "recommendations": recs, "valid": True}
            except (json.JSONDecodeError, ValidationError) as e:
                errs = [str(e)[:500]]
            if attempt == 0:                             # one retry with the exact errors
                self.messages.append({"role": "user", "content":
                    f"Your last reply was invalid: {errs}. Reply again with ONE valid "
                    "JSON object only, following the format in your instructions."})
                msg = self._call_model(tool_choice="none")
                raw = msg.content or ""
                self.messages.append({"role": "assistant", "content": raw})
        return {"message": "Sorry, I couldn't produce a valid answer. Please try again.",
                "recommendations": None, "valid": False}
