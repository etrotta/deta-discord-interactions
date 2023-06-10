class DatabaseError(Exception):
    "Base Exception class used by the deta-discord-interactions Database module"

class KeyNotFound(DatabaseError):
    "Key does not exists in the Deta Base"

class UnexpectedFunction(DatabaseError):
    "Function not registered in the database trying to encode or decode the record"

class UnexpectedEscapeString(DatabaseError):
    "String starts with `$` reserved character, but does not matches any planned conversions"

class DriveOutOfBoundsError(DatabaseError):
    "Drive Path tries to go beyond the root using `..`"
