from enum import Enum


class Service(Enum):
    OBJECT_STORAGE  = 'objectStorage'
    QUEUE           = 'queue'
    FIFO_QUEUE      = 'fifoQueue'
    PUBSUB          = 'pubsub'
