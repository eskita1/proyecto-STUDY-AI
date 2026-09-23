# StudyAI

StudyAI es una plataforma de acompañamiento académico para estudiantes universitarios. Busca ayudar a organizar materias, unidades y temas, y a entender el avance académico de forma clara.

El proyecto está en una etapa inicial. Actualmente cuenta con un backend mínimo en FastAPI y un endpoint de salud. Todavía no incluye gestión de materias, autenticación, base de datos, frontend ni funcionalidades de IA.

## Objetivo

Construir una base simple y consistente para que, de manera gradual, el producto pueda registrar la estructura académica del estudiante y luego acompañarlo en su estudio. Las métricas académicas importantes tendrán reglas determinísticas; la IA será una ayuda futura, no su fuente de verdad.

## Stack actual

- Python
- FastAPI
- Uvicorn

## Ejecutar el backend

Desde la carpeta `backend/`, crear y activar un entorno virtual si todavía no existe, instalar las dependencias y ejecutar el servidor:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

El endpoint `GET /health` responde con el estado del servicio.

## Documentación

- [Producto](docs/product.md): problema, visión y principios de StudyAI.
- [Dominio](docs/domain.md): conceptos académicos centrales y sus relaciones.
- [Roadmap](docs/roadmap.md): evolución prevista del producto.
- [Decisiones de producto](docs/decisions/product/README.md): decisiones que orientan el producto.
- [Decisiones técnicas](docs/decisions/technical/README.md): decisiones sobre la base técnica.
- [Cómo contribuir](CONTRIBUTING.md): pautas breves para proponer cambios.
