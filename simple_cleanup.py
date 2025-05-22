#!/usr/bin/env python
"""
Простая очистка ненужных файлов в проекте.
"""
import os
import shutil
from pathlib import Path

def cleanup_project():
    """Очищает проект от ненужных файлов."""
    print("🧹 ОЧИСТКА ПРОЕКТА")
    print("=" * 50)
    
    # Файлы и папки для удаления (относительно корня проекта)
    files_to_remove = [
        # Старые скрипты инициализации  
        "init_agents.py",  # пустой файл
        "init_agents_old.py",
        
        # Тестовые и отладочные скрипты
        "debug_init.py",
        "check_env.py", 
        "check_imports.py",
        
        # Старые скрипты
        "fix_and_run.sh",
        
        # Логи
        "agents_init.log",
        "bot.log",
        
        # Кэш Python в корне
        "__pycache__",
        
        # Резервные копии в app
        "app/learning/questions.py.backup"
    ]
    
    removed_count = 0
    total_size = 0
    
    print("📋 СПИСОК ДЛЯ УДАЛЕНИЯ:")
    
    for item in files_to_remove:
        path = Path(item)
        if path.exists():
            try:
                if path.is_file():
                    size = path.stat().st_size
                    print(f"   📄 {item} ({size} байт)")
                    total_size += size
                elif path.is_dir():
                    dir_size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                    print(f"   📁 {item}/ ({dir_size} байт)")
                    total_size += dir_size
            except:
                print(f"   ❓ {item}")
        else:
            print(f"   ⚠️ {item} (не найден)")
    
    print(f"\n📊 ОБЩИЙ РАЗМЕР: {total_size} байт ({total_size/1024:.1f} KB)")
    
    # Подтверждение
    response = input(f"\n❓ Удалить эти файлы? (yes/no): ").lower().strip()
    if response not in ['yes', 'y', 'да']:
        print("❌ Очистка отменена")
        return
    
    print("\n🗑️ УДАЛЕНИЕ...")
    
    for item in files_to_remove:
        path = Path(item)
        if path.exists():
            try:
                if path.is_file():
                    path.unlink()
                    print(f"✅ Удален файл: {item}")
                    removed_count += 1
                elif path.is_dir():
                    shutil.rmtree(path)
                    print(f"✅ Удалена папка: {item}")
                    removed_count += 1
            except Exception as e:
                print(f"❌ Ошибка удаления {item}: {e}")
    
    print(f"\n✨ УДАЛЕНО: {removed_count} элементов")
    
    # Показываем что осталось в корне
    print("\n📂 ОСТАВШИЕСЯ ФАЙЛЫ В КОРНЕ:")
    root_files = [f for f in Path(".").glob("*") if f.is_file() and not f.name.startswith('.')]
    for file in sorted(root_files):
        size = file.stat().st_size
        print(f"   📄 {file.name} ({size} байт)")
    
    print("\n🎉 ОЧИСТКА ЗАВЕРШЕНА!")
    print("🚀 Проект готов к работе!")

def show_project_structure():
    """Показывает структуру проекта."""
    print("\n📋 СТРУКТУРА ПРОЕКТА:")
    print("=" * 30)
    
    important_items = [
        ("📄 init_agents_final.py", "Скрипт инициализации AI-агентов"),
        ("📄 requirements.txt", "Зависимости Python"),
        ("📄 .env", "Конфигурация (токены)"), 
        ("📄 README.md", "Документация"),
        ("📁 app/", "Основной код бота"),
        ("📁 app/bot/", "Telegram bot handlers"),
        ("📁 app/database/", "Работа с БД"),
        ("📁 app/langchain/", "AI агенты"),
        ("📁 app/knowledge/", "База знаний"),
        ("📁 app/learning/", "Логика обучения"),
        ("📄 risk_training.db", "База данных SQLite")
    ]
    
    for item, description in important_items:
        print(f"   {item:<25} - {description}")
    
    print("\n✅ ОСНОВНЫЕ КОМПОНЕНТЫ:")
    print("   🤖 Telegram Bot с AI агентами")
    print("   🧠 LLM интеграция (qwen2.5-14b-instruct)")
    print("   📚 Система обучения рискам")
    print("   💾 SQLite база данных")

if __name__ == "__main__":
    cleanup_project()
    show_project_structure()
    
    print("\n🚀 СЛЕДУЮЩИЙ ШАГ:")
    print("   python -m app.main")
    print("   (запуск AI-бота)")