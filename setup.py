from cx_Freeze import setup, Executable

setup(
    name="analyze_performance",
    version="1.0",
    description="실적 분석 도구",
    executables=[Executable("src/reporting/analyze_performance_simple.py")]
)