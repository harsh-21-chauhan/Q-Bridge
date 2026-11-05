"""One reliable local startup command: python -m backend.run --live.

The key is entered privately and passed through the backend process environment.
It is never written to a file, printed, or placed in a command-line argument.
Starting the server does not call Meta.
"""
import argparse
import getpass
import os
import socket


def port_available(port):
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', port))
        except OSError:
            return False
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Enable deliberately submitted Muse Spark requests; prompts for a key if needed.')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error('Port must be between 1 and 65535.')
    if not port_available(args.port):
        parser.error(f'Port {args.port} is already in use. Stop the old backend with Ctrl+C in its terminal, then run this command again.')

    import uvicorn
    from backend.app.config import Settings
    from backend.app.services.assistant_service import AssistantService

    if args.live:
        key = os.environ.get('MODEL_API_KEY', '').strip()
        if not key:
            key = getpass.getpass('Paste Meta API key (hidden; press Enter): ').strip()
        if not key or not key.isascii() or any(c.isspace() for c in key):
            parser.error('A nonempty API key without spaces is required. Nothing was sent to Meta.')
        os.environ['MODEL_API_KEY'] = key
    # Explicit startup mode takes precedence over stale exports in this terminal.
    os.environ['QBRIDGE_ASSISTANT_MODE'] = 'live' if args.live else 'mock'
    os.environ['QBRIDGE_LIVE_AUTHORIZED'] = 'yes' if args.live else 'no'
    os.environ['QBRIDGE_ASSISTANT_DISABLED'] = 'false'
    settings = Settings.from_environment()
    service = AssistantService(None, settings.experiment_dir.parent / 'assistant')
    service.resume()  # Clears pause only, never budget history.
    print(f"Q-Bridge: {'LIVE enabled' if args.live else 'mock mode'}. No model request has been sent.")
    print('Usage limits retained. Stop with Ctrl+C. Keep this terminal open.')
    uvicorn.run('backend.app.main:app', host='127.0.0.1', port=args.port, reload=True)


if __name__ == '__main__':
    main()
