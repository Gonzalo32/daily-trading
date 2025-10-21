# Guía de Contribución

¡Gracias por tu interés en contribuir al Bot de Day Trading! 🚀

## 📋 Cómo Contribuir

### 1. Fork del Repositorio
- Haz fork del repositorio en GitHub
- Clona tu fork localmente:
```bash
git clone https://github.com/tu-usuario/daily-trading.git
cd daily-trading
```

### 2. Configurar el Entorno de Desarrollo
```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt
```

### 3. Crear una Rama
```bash
git checkout -b feature/nueva-funcionalidad
# o
git checkout -b fix/correccion-bug
```

### 4. Hacer Cambios
- Sigue las convenciones de código del proyecto
- Añade tests para nuevas funcionalidades
- Actualiza la documentación si es necesario
- Asegúrate de que todos los tests pasen

### 5. Commit y Push
```bash
git add .
git commit -m "feat: añadir nueva funcionalidad"
git push origin feature/nueva-funcionalidad
```

### 6. Crear Pull Request
- Ve a GitHub y crea un Pull Request
- Describe claramente los cambios realizados
- Menciona cualquier issue relacionado

## 🎯 Tipos de Contribuciones

### 🐛 Reportar Bugs
- Usa el template de issue para bugs
- Incluye pasos para reproducir el problema
- Añade información del sistema y versión

### ✨ Sugerir Mejoras
- Usa el template de issue para mejoras
- Describe la funcionalidad deseada
- Explica por qué sería útil

### 📝 Mejorar Documentación
- Corrige errores tipográficos
- Añade ejemplos de uso
- Mejora la claridad de las explicaciones

### 🔧 Mejorar Código
- Optimiza algoritmos existentes
- Añade nuevas funcionalidades
- Corrige bugs
- Mejora la estructura del código

## 📏 Estándares de Código

### Python
- Sigue PEP 8
- Usa type hints cuando sea posible
- Documenta funciones y clases
- Mantén líneas bajo 127 caracteres

### Estructura de Commits
Usa el formato Conventional Commits:
```
tipo(scope): descripción

[body opcional]

[footer opcional]
```

Tipos:
- `feat`: nueva funcionalidad
- `fix`: corrección de bug
- `docs`: cambios en documentación
- `style`: cambios de formato
- `refactor`: refactorización de código
- `test`: añadir o modificar tests
- `chore`: tareas de mantenimiento

### Ejemplos
```
feat(strategy): añadir estrategia de momentum
fix(risk): corregir cálculo de drawdown
docs(readme): actualizar instrucciones de instalación
```

## 🧪 Testing

### Ejecutar Tests
```bash
# Todos los tests
pytest

# Tests específicos
pytest tests/test_strategy.py

# Con cobertura
pytest --cov=src tests/
```

### Escribir Tests
- Tests unitarios para funciones individuales
- Tests de integración para flujos completos
- Tests de backtesting para estrategias
- Mocks para APIs externas

## 📚 Documentación

### README
- Mantén actualizado el README principal
- Añade ejemplos de uso
- Documenta nuevas funcionalidades

### Docstrings
```python
def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calcular RSI (Relative Strength Index)
    
    Args:
        prices: Serie de precios
        period: Período para el cálculo (default: 14)
        
    Returns:
        Serie con valores de RSI
        
    Raises:
        ValueError: Si el período es menor a 2
    """
```

### Comentarios
- Explica la lógica compleja
- Documenta decisiones de diseño
- Añade contexto cuando sea necesario

## 🔍 Code Review

### Como Revisor
- Revisa el código cuidadosamente
- Verifica que los tests pasen
- Sugiere mejoras constructivas
- Aproba solo si estás seguro

### Como Autor
- Responde a los comentarios
- Haz los cambios solicitados
- Explica tu razonamiento
- Mantén la conversación constructiva

## 🚀 Proceso de Release

### Versiones
- Seguimos Semantic Versioning (MAJOR.MINOR.PATCH)
- MAJOR: cambios incompatibles
- MINOR: nuevas funcionalidades compatibles
- PATCH: correcciones de bugs

### Changelog
- Actualiza CHANGELOG.md
- Documenta todos los cambios
- Agrupa por tipo de cambio
- Incluye enlaces a PRs

## 🤝 Comportamiento Esperado

### Respeto
- Sé respetuoso con otros contribuidores
- Mantén un tono profesional
- Evita comentarios personales

### Constructividad
- Sugiere mejoras, no solo críticas
- Explica el por qué de tus sugerencias
- Ofrece alternativas cuando sea posible

### Colaboración
- Trabaja en equipo
- Comparte conocimiento
- Ayuda a otros contribuidores

## 📞 Contacto

- 📧 Email: contribuciones@tradingbot.com
- 💬 Discord: [Servidor de la Comunidad](https://discord.gg/tradingbot)
- 🐛 Issues: [GitHub Issues](https://github.com/tu-usuario/daily-trading/issues)

## 📄 Licencia

Al contribuir, aceptas que tu código será licenciado bajo la [Licencia MIT](LICENSE).

---

¡Gracias por contribuir al Bot de Day Trading! 🎉
