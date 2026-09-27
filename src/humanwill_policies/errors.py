class PolicyError(ValueError):
    """Expected validation failure with a stable, machine-readable code."""

    def __init__(self, code: str, message: str, location: str = ""):
        self.code = code
        self.message = message
        self.location = location
        super().__init__(f"{code}: {message}" + (f" ({location})" if location else ""))

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "location": self.location}
