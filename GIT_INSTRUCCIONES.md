# 📦 Instrucciones para Git

## 🎯 Preparar para commit

### 1️⃣ Verificar estado

```bash
git status
```

Deberías ver archivos como:
- ✅ `README.md` (nuevo)
- ✅ `env.example` (nuevo)
- ✅ `setup_windows.bat` (nuevo)
- ✅ `.gitignore` (modificado)
- ✅ `CAMBIOS_UNIFICACION_PNL.md` (nuevo)
- ✅ Archivos `.py` modificados
- ❌ `venv/` (ignorado)
- ❌ `logs/` (ignorado)
- ❌ `state.json` (ignorado)
- ❌ `.env` (ignorado)

### 2️⃣ Agregar archivos al staging

```bash
# Agregar todos los cambios relevantes
git add .

# O selectivamente:
git add README.md
git add env.example
git add setup_windows.bat
git add .gitignore
git add CAMBIOS_UNIFICACION_PNL.md
git add daily-trading/main.py
git add daily-trading/src/risk/risk_manager.py
git add daily-trading/src/ml/trade_recorder.py
git add daily-trading/src/state/state_manager.py
git add start.bat
```

### 3️⃣ Commit con mensaje descriptivo

```bash
git commit -m "feat: estabilización completa - PnL unificado, sizing corregido, persistencia implementada"
```

O con mensaje más detallado:

```bash
git commit -m "feat: estabilización completa del bot

- Unificar PnL en RiskManager como única fuente de verdad
- Corregir bug de sizing (0.011 -> 10.646 BTC)
- Fix TradeRecorder: manejar r_value=None sin crash
- Fix encoding UTF-8 en Windows
- Implementar persistencia de estado (StateManager)
- Agregar límite de exposición (50% equity)
- Crear README completo y setup automático
- Smoke tests pasados (3/3)"
```

### 4️⃣ Push al repositorio

```bash
# Si es tu primera vez:
git remote add origin <tu-repo-url>
git branch -M main
git push -u origin main

# Si ya existe:
git push
```

---

## 🔄 Clonar en otra computadora

### 1️⃣ Clonar el repositorio

```bash
git clone <tu-repo-url>
cd daily-trading
```

### 2️⃣ Setup automático (Windows)

```bash
setup_windows.bat
```

O manualmente:

```bash
# Crear venv
python -m venv venv
venv\Scripts\activate

# Instalar dependencias
cd daily-trading
pip install -r requirements.txt
```

### 3️⃣ Configurar (opcional)

```bash
# Copiar y editar .env
copy env.example .env
notepad .env
```

### 4️⃣ Ejecutar

```bash
start.bat
```

---

## 📋 Checklist Pre-Commit

Antes de hacer commit, verifica:

- [ ] `.gitignore` está actualizado
- [ ] No hay secretos en el código (API keys, passwords)
- [ ] `requirements.txt` está completo
- [ ] `README.md` tiene instrucciones claras
- [ ] `env.example` tiene todas las variables
- [ ] Smoke tests pasan (ejecuta: `python -c "import main"`)
- [ ] No hay archivos de log/estado en staging (`git status`)

---

## 🗂️ Archivos que NO deben estar en git

Estos archivos están en `.gitignore` y NO se deben commitear:

```
venv/                    # Entorno virtual
__pycache__/            # Cache de Python
*.pyc, *.pyo            # Bytecode
.env                    # Configuración local
state.json              # Estado del bot
logs/                   # Logs
*.log                   # Archivos de log
models/                 # Modelos ML (son grandes)
training_data.csv       # Dataset (puede ser grande)
```

---

## 🔍 Verificar qué se va a commitear

```bash
# Ver archivos en staging
git status

# Ver diferencias
git diff

# Ver diferencias en staging
git diff --staged
```

---

## 🚨 Si agregaste algo por error

```bash
# Quitar archivo del staging
git reset HEAD archivo.txt

# Quitar todos del staging
git reset HEAD .

# Descartar cambios locales (⚠️ PELIGRO)
git checkout -- archivo.txt
```

---

## 🌿 Branches (opcional)

Si quieres trabajar en features separadas:

```bash
# Crear branch
git checkout -b feature/nueva-feature

# Cambiar entre branches
git checkout main
git checkout feature/nueva-feature

# Merge a main
git checkout main
git merge feature/nueva-feature

# Eliminar branch
git branch -d feature/nueva-feature
```

---

## 📝 Mensajes de commit recomendados

Usa prefijos para claridad:

- `feat:` - Nueva funcionalidad
- `fix:` - Corrección de bug
- `docs:` - Documentación
- `refactor:` - Refactorización
- `test:` - Tests
- `chore:` - Mantenimiento

Ejemplos:
```bash
git commit -m "feat: agregar persistencia de estado"
git commit -m "fix: corregir bug de sizing en size_and_protect"
git commit -m "docs: actualizar README con instrucciones de setup"
git commit -m "refactor: unificar PnL en RiskManager"
```

---

## 🔐 .gitignore Explicado

```gitignore
# Python
venv/              # Tu entorno virtual local
__pycache__/      # Cache de Python
*.pyc             # Bytecode compilado

# Configuración
.env              # TUS credenciales locales

# Estado
state.json        # Estado de TU bot

# Logs
logs/             # Logs de TU instancia

# Data
training_data.csv # Dataset generado localmente
```

---

## ✅ Todo listo

Después de seguir estos pasos:

1. ✅ Tu código está en git
2. ✅ Puedes clonarlo en cualquier computadora
3. ✅ Setup automático con `setup_windows.bat`
4. ✅ No expones secretos ni estado local

---

**Última actualización:** 2026-01-12
