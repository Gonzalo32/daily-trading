# 🛠️ Tools - Scripts de Diagnóstico

Esta carpeta contiene scripts de utilidad para diagnóstico y mantenimiento del proyecto.

---

## 📊 collect_diagnostics.ps1

Script de PowerShell que genera un reporte completo del estado del proyecto.

### 🚀 Uso

**Desde la raíz del proyecto:**

```powershell
powershell -ExecutionPolicy Bypass -File tools\collect_diagnostics.ps1
```

**O si estás en PowerShell:**

```powershell
cd C:\Users\gonza\OneDrive\Desktop\daily-trading
.\tools\collect_diagnostics.ps1
```

### 📄 Output

El script genera:

1. **`diagnostics/REPORT.md`** - Reporte principal en markdown
2. **`diagnostics/COMMANDS.log`** - Log detallado de todos los comandos ejecutados

### 🔍 Qué Diagnostica

El script verifica:

#### 1️⃣ Entorno Python
- ✅ Versión de Python y pip
- ✅ Ruta del virtualenv activo
- ✅ Variables de entorno

#### 2️⃣ Estado del Repositorio
- ✅ Git status
- ✅ Estructura de archivos (tree)
- ✅ Archivos en raíz

#### 3️⃣ Dependencias
- ✅ Contenido de `requirements.txt`
- ✅ Conflictos de dependencias (`pip check`)
- ✅ Paquetes instalados (`pip freeze`)

#### 4️⃣ Import Sanity (Crítico)
- ✅ `import main` → Verifica entrypoint principal
- ✅ `import src.main` → Verifica imports relativos
- ✅ `from src.ml.ml_signal_filter import MLSignalFilter` → Verifica módulo ML
- ✅ `from src.ml.trade_recorder import TradeRecorder` → Verifica recorder

**Esto detecta el error crítico:**
```
'MLSignalFilter' object has no attribute 'is_model_available'
```

#### 5️⃣ Entry Points
- ✅ Detecta todos los `main.py` posibles
- ✅ Identifica cuál es el correcto

#### 6️⃣ Datos ML
- ✅ Lista archivos en `src/ml/`
- ✅ Verifica existencia de `training_data.csv`
- ✅ Muestra primeras 10 filas del CSV (si existe)

#### 7️⃣ Linting
- ✅ Versión de pylint
- ✅ Errores de lint en `main.py` y `src/`

---

## 🎯 Casos de Uso

### Caso 1: Error MLSignalFilter

**Problema:** Bot crashea con error `is_model_available`

**Solución:**
```powershell
# 1. Generar diagnóstico
.\tools\collect_diagnostics.ps1

# 2. Ver sección "Import smoke: MLSignalFilter" en diagnostics/REPORT.md
# 3. Si falla el import → limpiar cache

# Limpiar cache Python
Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force

# 4. Re-ejecutar diagnóstico
.\tools\collect_diagnostics.ps1
```

---

### Caso 2: Verificar Estructura Antes de Commit

**Antes de hacer commit:**

```powershell
# Generar diagnóstico
.\tools\collect_diagnostics.ps1

# Verificar en diagnostics/REPORT.md:
# ✅ Git status → archivos tracked
# ✅ pip check → sin conflictos
# ✅ Import smoke → todos OK
# ✅ pylint → sin errores críticos
```

---

### Caso 3: Debugging en Producción

**Bot falla en servidor remoto:**

```powershell
# 1. Ejecutar en servidor
.\tools\collect_diagnostics.ps1

# 2. Copiar diagnostics/REPORT.md localmente
# 3. Revisar secciones:
#    - Virtualenv activo → verificar venv correcto
#    - pip check → conflictos de dependencias
#    - Import smoke → módulos faltantes
```

---

### Caso 4: Onboarding Nuevo Desarrollador

**Setup inicial:**

```powershell
# 1. Clonar repo
git clone <repo-url>
cd daily-trading

# 2. Crear venv
python -m venv venv
.\venv\Scripts\activate

# 3. Instalar deps
pip install -r requirements.txt

# 4. Verificar todo OK
.\tools\collect_diagnostics.ps1

# 5. Revisar diagnostics/REPORT.md
# ✅ Todos los imports smoke deben pasar
```

---

## 🔧 Troubleshooting

### Error: "No se puede ejecutar scripts en este sistema"

**Solución:**

```powershell
# Opción 1: Ejecutar con bypass (recomendado)
powershell -ExecutionPolicy Bypass -File tools\collect_diagnostics.ps1

# Opción 2: Cambiar política permanentemente (admin)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### Error: "requirements.txt no encontrado"

**Causa:** Script ejecutado desde directorio incorrecto

**Solución:**

```powershell
# Ir a raíz del proyecto
cd C:\Users\gonza\OneDrive\Desktop\daily-trading

# Verificar que estás en el lugar correcto
dir requirements.txt

# Ejecutar script
.\tools\collect_diagnostics.ps1
```

---

### Error: "tree command not found"

**Solución:**

El comando `tree` es nativo de Windows. Si no funciona:

```powershell
# Alternativa manual
Get-ChildItem -Recurse -Depth 2 | Select-Object FullName
```

---

## 📊 Ejemplo de Output

**diagnostics/REPORT.md:**

```markdown
## Reporte de Diagnóstico - daily-trading
Fecha: 2026-01-12 15:30:45

### Python y pip (rutas)
```
> where python; python --version; python -m pip --version
```
```
C:\Users\gonza\OneDrive\Desktop\daily-trading\venv\Scripts\python.exe
Python 3.11.5
pip 23.3.1 from C:\...\site-packages\pip (python 3.11)
```

### Import smoke: MLSignalFilter
```
> python -c "from src.ml.ml_signal_filter import MLSignalFilter; print('OK MLSignalFilter')"
```
```
OK MLSignalFilter
```

### training_data.csv head
```
timestamp,symbol,side,entry_price,exit_price,pnl,...
(vacío o con datos)
```
```

---

## 🎯 Próximos Scripts

Scripts futuros a agregar en esta carpeta:

- [ ] `clean_cache.ps1` - Limpia `__pycache__` y `.pyc`
- [ ] `check_health.ps1` - Verifica bot running, logs recientes, posiciones abiertas
- [ ] `export_metrics.ps1` - Exporta métricas de SQLite a CSV
- [ ] `backup_data.ps1` - Backup de CSV ML, models, config

---

**Mantenido por:** Bot Team  
**Última actualización:** 12 enero 2026
