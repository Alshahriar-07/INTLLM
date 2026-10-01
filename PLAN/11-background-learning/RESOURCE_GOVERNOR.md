# Background Resource Governor

Background learning must never degrade normal chat experience beyond configured thresholds.

Signals:

- CPU usage
- RAM pressure
- GPU utilization if detectable
- queue length
- time-to-first-token
- current interactive requests

States:

```text
NORMAL -> background allowed
BUSY -> background throttled
CRITICAL -> background paused
```

When interactive load drops, resume gradually.

Never start an unlimited number of background workers.
