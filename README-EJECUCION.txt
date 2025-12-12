═══════════════════════════════════════════════════════════
🤖 BOT DE TRADING - GUÍA DE EJECUCIÓN RÁPIDA
═══════════════════════════════════════════════════════════

📍 UBICACIÓN ACTUAL
-------------------
C:\Users\Administrador\Desktop\daily-trading


🚀 COMANDOS DISPONIBLES
-----------------------

🔵 SI USAS CMD (Símbolo del sistema):
   
   start        → Inicia el bot completo
   quick        → Ejecuta un ciclo único


🟣 SI USAS POWERSHELL:
   
   .\start      → Inicia el bot completo
   .\bot        → Alias corto para start
   .\quick      → Ejecuta un ciclo único


📌 NOTA: PowerShell requiere .\ antes del comando


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DESCRIPCIÓN:

1. INICIO NORMAL (Bot completo con bucle continuo)
   
   Ejecuta: daily-trading\main.py
   
   Este es el bot principal que se ejecuta continuamente
   monitoreando el mercado y ejecutando trades automáticamente.


2. CICLO ÚNICO (Una sola iteración)
   
   Ejecuta: daily-trading\src\main.py
   
   Ejecuta un solo ciclo de trading y termina.
   Útil para pruebas rápidas.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 OPCIÓN AVANZADA (Alias permanente en PowerShell):

   Si quieres escribir solo "bot" sin el .\ ejecuta:
   
   .\configurar-powershell
   
   Esto creará un alias permanente. Después podrás usar:
   
   bot          → Desde cualquier ubicación


📝 NOTAS IMPORTANTES
--------------------

✅ Los scripts automáticamente:
   • Activan el entorno virtual (venv)
   • Ejecutan el programa
   • Desactivan el entorno virtual al terminar

⚠️  Asegúrate de tener configurado:
   • Archivo .env con tus credenciales de API
   • Entorno virtual instalado (venv)
   • Dependencias instaladas (requirements.txt)


🔧 SOLUCIÓN DE PROBLEMAS
------------------------

❌ Si en PowerShell aparece "Proporcione valores para FilePath":
   → Usa: .\start (con el .\ al principio)
   → O usa: .\bot
   → PowerShell requiere .\ para ejecutar scripts locales

❌ Si aparece "comando no reconocido":
   → En CMD: start.bat (con la extensión completa)
   → En PowerShell: .\start.ps1

❌ Si no encuentra el entorno virtual:
   → Verifica que existe: daily-trading\venv\

❌ Si falta alguna dependencia:
   → cd daily-trading
   → venv\Scripts\activate
   → pip install -r requirements.txt

❌ Si PowerShell bloquea la ejecución de scripts:
   → Ejecuta como Administrador:
   → Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser


═══════════════════════════════════════════════════════════

