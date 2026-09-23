# Dominio

Este documento describe el lenguaje principal de StudyAI. No define todavía una base de datos ni una implementación técnica.

## Conceptos académicos principales

- **Student / User:** la persona que usa StudyAI para acompañar su recorrido académico. Mientras no exista autenticación, ambos términos se usan como conceptos de producto, no como una implementación.
- **Course:** una materia cursada por el estudiante.
- **Unit:** una unidad o bloque temático dentro de una materia.
- **Topic:** un tema concreto dentro de una unidad. Es la parte más pequeña de la estructura académica que se espera poder seguir inicialmente.

La relación conceptual es:

```text
Student / User
└── Course
    └── Unit
        └── Topic
```

Un estudiante puede tener varias materias. Cada materia organiza su contenido en unidades y cada unidad contiene temas.

## Métricas académicas

Las siguientes métricas responden preguntas diferentes y no deben confundirse.

### Progress

Indica cuánto del contenido de una materia completó o recorrió el estudiante. Responde: **¿cuánto contenido hice?**

### Course Pace

Indica la posición del estudiante respecto del avance actual de la cursada. Responde: **¿estoy al día, adelantado o atrasado respecto de la materia?**

### Mastery

Indica qué tan bien domina el estudiante un tema que estudió o practicó. Responde: **¿qué tan bien entiendo o puedo aplicar este tema?**

Por ejemplo, un estudiante puede haber avanzado poco en una materia (*Progress* bajo), estar al día con lo que se dictó hasta ahora (*Course Pace* adecuado) y dominar muy bien los temas vistos (*Mastery* alto). Cada métrica deberá tener reglas explícitas cuando se implemente.
