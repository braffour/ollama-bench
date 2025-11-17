"""
Message handling and communication between agents.
"""

class Message:
    """Base message class for inter-agent communication."""

    def __init__(self, sender, recipient, content):
        """Initialize a message."""
        self.sender = sender
        self.recipient = recipient
        self.content = content
        self.timestamp = None

class BenchmarkRequest(Message):
    """Request message for initiating a benchmark."""

    def __init__(self, sender, recipient, benchmark_config):
        """Initialize benchmark request."""
        super().__init__(sender, recipient, benchmark_config)

class BenchmarkResult(Message):
    """Result message containing benchmark outcomes."""

    def __init__(self, sender, recipient, results):
        """Initialize benchmark result."""
        super().__init__(sender, recipient, results)
