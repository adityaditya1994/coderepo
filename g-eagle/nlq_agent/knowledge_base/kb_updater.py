"""
KB Updater — feedback loop that updates the knowledge base
based on user corrections and validated query patterns.
"""

from knowledge_base.metrics_store import MetricsStore


class KBUpdater:
    """Process user feedback and update the metrics knowledge base."""

    def __init__(self, metrics_store: MetricsStore = None):
        self.store = metrics_store or MetricsStore()

    def process_feedback(self, state: dict, feedback: str):
        """
        Process user feedback after a query completes.

        Parameters
        ----------
        state : dict
            The full agent state after summarization.
        feedback : str
            User feedback: "correct", "incorrect", or a correction string.
        """
        query_plan = state.get("query_plan", {})
        sql = state.get("sql", "")
        metrics_used = query_plan.get("metrics", [])

        if feedback.lower() == "correct":
            # User confirmed — approve any unapproved metrics that were used
            for metric_name in metrics_used:
                existing = self.store.lookup(metric_name)
                if existing and not existing.get("approved"):
                    self.store.approve(metric_name, approved_by="user_feedback")

        elif feedback.lower() == "incorrect":
            # User says result is wrong — flag metrics as needing review
            for metric_name in metrics_used:
                existing = self.store.lookup(metric_name)
                if existing:
                    existing["approved"] = False
                    existing["updated_by"] = "needs_review"
                    self.store.metrics[metric_name] = existing
                    self.store.save()

        else:
            # Treat as a correction — store the feedback for future reference
            # In production, this could trigger a re-definition flow
            pass

    def suggest_new_metric(
        self,
        name: str,
        definition: str,
        sql_expression: str,
        table: str,
        filters: str = "",
    ):
        """
        Suggest a new metric found during query planning.
        Stored as unapproved until a human confirms.
        """
        existing = self.store.lookup(name)
        if existing:
            return  # Don't overwrite existing definitions

        self.store.add_or_update(
            name=name,
            definition=definition,
            sql_expression=sql_expression,
            table=table,
            filters=filters,
            approved=False,
            updated_by="auto_suggested",
        )
