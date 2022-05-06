from enum import Enum


class Trigger(Enum):
    OBJECT_STORAGE  = 'objectStorage'
    DOCUMENT_STORE  = 'documentStore'
    QUEUE           = 'queue'
    FIFO_QUEUE      = 'fifoQueue'
    PUBSUB          = 'pubsub'
    TIMER           = 'timer'
