"""Exercise HTTP readiness and a real Streamlit session through the public proxy."""
import argparse
import asyncio
from urllib.parse import urlsplit
from urllib.request import urlopen

import websockets
from streamlit.proto.BackMsg_pb2 import BackMsg
from streamlit.proto.ForwardMsg_pb2 import ForwardMsg


async def check_websocket(origin):
    parsed = urlsplit(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("Supply an HTTP(S) origin without credentials or a path.")
    scheme = "wss" if parsed.scheme == "https" else "ws"
    async with websockets.connect(
        f"{scheme}://{parsed.netloc}/_stcore/stream", origin=origin.rstrip("/"),
        subprotocols=["streamlit"], open_timeout=5, max_size=16 * 1024 * 1024,
    ) as socket:
        request = BackMsg()
        request.rerun_script.query_string = ""
        await socket.send(request.SerializeToString())
        kinds = set()
        for _ in range(500):
            response = ForwardMsg()
            response.ParseFromString(await asyncio.wait_for(socket.recv(), timeout=30))
            kind = response.WhichOneof("type")
            kinds.add(kind)
            if kind == "delta" and response.delta.HasField("new_element") and response.delta.new_element.HasField("exception"):
                raise RuntimeError("Streamlit reported an application exception.")
            if kind == "script_finished":
                if response.script_finished == ForwardMsg.FINISHED_WITH_COMPILE_ERROR:
                    raise RuntimeError("Streamlit reported a compilation error.")
                if response.script_finished == ForwardMsg.FINISHED_SUCCESSFULLY:
                    if not {"new_session", "delta"}.issubset(kinds):
                        raise RuntimeError("No complete application session received.")
                    return
        raise RuntimeError("Streamlit did not finish the application run.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:10000")
    args = parser.parse_args()
    with urlopen(args.url.rstrip("/") + "/_deployment/ready", timeout=5) as response:
        if response.status != 200:
            raise RuntimeError("Readiness check failed.")
    asyncio.run(check_websocket(args.url))
    print("HTTP readiness and Streamlit WebSocket session: OK")


if __name__ == "__main__":
    main()
