import os
from dotenv import load_dotenv
from openai import OpenAI
import requests

load_dotenv()

print("=" * 60)
print("SMOKE TEST: Validando APIs de xAI y Buttondown")
print("=" * 60)

# TEST 1: xAI
print("\n[1/2] Probando xAI API...")
try:
    client = OpenAI(
        api_key=os.environ["XAI_API_KEY"],
        base_url="https://api.x.ai/v1"
    )
    response = client.chat.completions.create(
        model="grok-4-1-fast",
        messages=[{"role": "user", "content": "Say hello"}]
    )
    print(f"OK xAI respondio: {response.choices[0].message.content}")
except Exception as e:
    print(f"ERROR xAI: {e}")
    exit(1)

# TEST 2: Buttondown
print("\n[2/2] Probando Buttondown API...")
try:
    headers = {
        "Authorization": f"Token {os.environ['BUTTONDOWN_API_KEY']}",
        "Content-Type": "application/json"
    }
    response = requests.post(
        "https://api.buttondown.com/v1/emails",
        headers=headers,
        json={
            "subject": "Test smoke test",
            "body": "Borrador de prueba. Puedes eliminarlo.",
            "status": "draft"
        }
    )
    if response.ok:
        print(f"OK Buttondown creo borrador: {response.json().get('id')}")
    else:
        print(f"ERROR Buttondown: {response.status_code} - {response.text}")
        exit(1)
except Exception as e:
    print(f"ERROR Buttondown: {e}")
    exit(1)

print("\n" + "=" * 60)
print("SMOKE TEST COMPLETADO: Ambas APIs funcionan correctamente")
print("=" * 60)