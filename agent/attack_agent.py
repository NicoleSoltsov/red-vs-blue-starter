"""
attack_agent.py  --  the agent loop.  >>> THIS IS THE FILE YOU COMPLETE. <<<

The idea of an "agent" is simple:
    1. We give the model a job (the system prompt) and a list of tools it can use.
    2. The model replies with ONE action at a time, written as JSON.
    3. Our code runs that tool and feeds the result back to the model.
    4. Repeat until the model says it's done, or we hit a safety step limit.

The plumbing (the loop, the JSON parsing, the tool dispatch, the printing) is
already written for you below. Your job is to fill in the parts marked
`TODO`:
    - Write the SYSTEM PROMPT that explains the job and the JSON format.
    - Make the agent report the EXACT vulnerable file and line number.
    - Add the step where the agent CONFIRMS the bug against the running app.

Run the target app first (see the README), then run this file.
"""

import json

from llm import chat
import tools

# How many steps the agent is allowed before we stop it. This is a safety net
# so a confused agent can't loop forever (and burn through your API credits).
MAX_STEPS = 12

# The folder the agent is allowed to read code from. ".." means the project
# root (one level up from this agent/ folder), so it can see target_app/.
CODEBASE_ROOT = ".."


# ---------------------------------------------------------------------------
#  TODO #1 -- THE SYSTEM PROMPT
# ---------------------------------------------------------------------------
# The system prompt is the model's instructions. Write it so the model knows:
#
#   * Its job: it is a security code-scanning agent looking for a SQL injection
#     vulnerability in the practice app's source code.
#   * The tools it can use and when:
#         list_files   -> {"action": "list_files", "root": "<folder>"}
#         read_file    -> {"action": "read_file", "root": "<folder>", "path": "<file>"}
#         send_request -> {"action": "send_request", "method": "GET"|"POST",
#                          "path": "<route>", "data": {<optional json>}}
#         finish       -> {"action": "finish", "answer": "<your final report>"}
#   * The RULES of the conversation:
#         - Reply with EXACTLY ONE JSON object and nothing else (no markdown,
#           no backticks, no explanation around it). Our parser reads one
#           action per turn.
#   * TODO #2: it must report the EXACT file and line number of the bug.
#   * TODO #3: before finishing, it must CONFIRM the bug by sending a real
#     request to the local app (e.g. an " ' OR '1'='1 " style login) and
#     checking the response proves the injection worked.
#
# Tip: keep it short and concrete. Show the model one example JSON action.
SYSTEM_PROMPT = """
TODO: Write the system prompt here. See the notes above for everything it
needs to cover (the job, the tool JSON formats, the one-JSON-per-reply rule,
reporting the exact file + line, and confirming the exploit live).
"""


def run_tool(action):
    """
    Look at the parsed JSON `action` and run the matching tool.

    Returns a string describing the result, which we hand back to the model.
    This part is DONE -- it simply connects the model's chosen action to the
    real functions in tools.py.
    """
    name = action.get("action")

    if name == "list_files":
        root = action.get("root", CODEBASE_ROOT)
        files = tools.list_files(root)
        return "Files found:\n" + "\n".join(files)

    if name == "read_file":
        root = action.get("root", CODEBASE_ROOT)
        path = action.get("path", "")
        return tools.read_file(root, path)

    if name == "send_request":
        result = tools.send_request(
            action.get("method", "GET"),
            action.get("path", "/"),
            action.get("data"),
        )
        return json.dumps(result)

    return "ERROR: unknown action '" + str(name) + "'."


def main():
    # The conversation starts with the system prompt, then a first user message
    # that kicks the agent off.
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Begin. Find the SQL injection vulnerability in the practice "
                "app, report the exact file and line, and confirm it works."
            ),
        },
    ]

    for step in range(1, MAX_STEPS + 1):
        print("\n" + "=" * 60)
        print("STEP " + str(step))
        print("=" * 60)

        # 1) Ask the model what to do next.
        reply = chat(messages)
        print("Agent says:\n" + reply)

        # Record the model's reply so it remembers its own train of thought.
        messages.append({"role": "assistant", "content": reply})

        # 2) Parse ONE JSON action out of the reply.
        try:
            action = json.loads(reply)
        except json.JSONDecodeError:
            # The model didn't give us clean JSON. Tell it so it can fix itself.
            feedback = (
                "Your last reply was not valid JSON. Reply with exactly one "
                "JSON object describing a single action, and nothing else."
            )
            print("\n[parser] " + feedback)
            messages.append({"role": "user", "content": feedback})
            continue

        # 3) If the model is finished, print its final answer and stop.
        if action.get("action") == "finish":
            print("\n" + "*" * 60)
            print("FINAL REPORT:")
            print(action.get("answer", "(no answer provided)"))
            print("*" * 60)
            return

        # 4) Otherwise run the chosen tool and feed the result back.
        result = run_tool(action)
        print("\nTool result:\n" + result)
        messages.append(
            {"role": "user", "content": "Tool result:\n" + result}
        )

    # If we fall out of the loop, the agent used up all its steps.
    print("\nReached the step limit (" + str(MAX_STEPS) + ") without finishing.")


if __name__ == "__main__":
    main()
