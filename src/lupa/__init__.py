"""Lupa: agente que responde preguntas sobre los datos abiertos de Colombia.

Módulos:
    config      Lee claves y parámetros desde .env o desde los secretos de Colab.
    llm         Capa común para hablar con distintos LLM (Gemini, Groq...).
    tools       Herramientas que el agente puede ejecutar (fase 2).
    agent       Ciclo razonar → actuar → observar (fase 3).
    ui          Interfaz Gradio (fase 5).
"""

__version__ = "0.1.0"
