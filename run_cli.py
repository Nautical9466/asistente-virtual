import sys
import os

# Ensure UTF-8 output encoding for Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from main import handle_incoming_message

def main():
    print("=" * 60)
    print("🤖 Virtual Assistant CLI Interactive Session (Claudia OS + LiteLLM)")
    print("=" * 60)
    print("Escribe tus mensajes a continuación. Presiona Ctrl+C o escribe 'salir' para terminar.\n")

    user_id = "cli_user"

    while True:
        try:
            user_input = input("\n👤 Tú: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["salir", "exit", "quit"]:
                print("👋 ¡Hasta luego!")
                break

            response = handle_incoming_message(user_input, user_id)
            print(f"\n🤖 Asistente:\n{response}")
            print("-" * 60)
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Sesión CLI finalizada.")
            break

if __name__ == "__main__":
    main()
