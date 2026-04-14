"""
NLQ Agent — CLI entry point.

Usage:
    cd nlq_agent
    python main.py
"""

import uuid
import sys

from config.config_loader import load_config
from graph.graph_builder import build_graph


def main():
    """Run the NLQ agent interactively."""
    print("=" * 60)
    print("  🦅 G-Eagle NLQ Agent")
    print("  Natural Language → SQL → Insights")
    print("=" * 60)

    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        print(f"\n❌ Failed to load config: {e}")
        sys.exit(1)

    # Build the graph
    try:
        graph = build_graph(config)
        print("✅ Agent graph compiled successfully.\n")
    except Exception as e:
        print(f"\n❌ Failed to build graph: {e}")
        sys.exit(1)

    session_id = str(uuid.uuid4())
    print(f"Session: {session_id}\n")

    while True:
        try:
            query = input("📝 Enter your question (or 'quit'): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye! 👋")
            break

        if query.lower() in ("quit", "exit", "q"):
            print("\nGoodbye! 👋")
            break

        if not query:
            continue

        # Build initial state
        initial_state = {
            "user_query": query,
            "session_id": session_id,
            "discovered_tables": [],
            "selected_tables": [],
            "schema": {},
            "query_plan": {},
            "sql": "",
            "sql_history": [],
            "execution_result": None,
            "execution_error": None,
            "retry_count": 0,
            "validation_result": {},
            "summary": "",
            "confidence_score": 0.0,
            "needs_human": False,
            "final_answer": None,
            "memory_context": {},
            "error_log": [],
        }

        # Run the graph
        thread_config = {"configurable": {"thread_id": session_id}}

        print("\n🔄 Processing...\n")

        try:
            result = graph.invoke(initial_state, config=thread_config)

            # Display result
            print("\n" + "─" * 60)
            if result.get("final_answer"):
                print(result["final_answer"])
            elif result.get("summary"):
                print(result["summary"])
            else:
                print("⚠️  No answer generated.")

            if result.get("needs_human"):
                print("\n⚠️  This query was escalated for human review.")

            # Show SQL if available
            if result.get("sql"):
                print(f"\n📊 SQL Used:\n{result['sql']}")

            # Show confidence
            confidence = result.get("confidence_score", 0.0)
            print(f"\n🎯 Confidence: {confidence:.2f}")
            print("─" * 60)

        except Exception as e:
            print(f"\n❌ Error: {e}")

        print()


if __name__ == "__main__":
    main()
