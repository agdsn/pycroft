import asyncio
import email
import email.policy
import sys

from aiosmtpd.controller import Controller
from termcolor import cprint


class PycroftDebugging:
    COLOR_HEADER = "blue"
    COLOR_CONTENT_BORDER = "magenta"

    async def handle_DATA(self, server, session, envelope):
        message = email.message_from_bytes(envelope.content, policy=email.policy.default)

        # Print headers
        for key, value in message.items():
            cprint(f"{key}: {value}", self.COLOR_HEADER)

        # Print message parts, i.e. text/plain, text/html
        for part in message.walk():
            try:
                content = part.get_content()
            except KeyError:
                continue

            print()
            content_type = part.get_content_type()
            cprint(content_type, self.COLOR_CONTENT_BORDER)
            cprint("⌄" * len(content_type), self.COLOR_CONTENT_BORDER)
            print(content)
            cprint("⌃" * len(content_type), self.COLOR_CONTENT_BORDER)

        print()
        sys.stdout.flush()

        return "250 Message accepted for delivery"


controller = Controller(PycroftDebugging(), hostname="0.0.0.0", port=2500)
controller.start()

loop = asyncio.get_event_loop()
try:
    loop.run_forever()
finally:
    loop.close()
    controller.stop()
