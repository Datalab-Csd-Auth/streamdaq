# :bulb: Good to Know

Practical notes that don't belong to a single feature.

## Jupyter notebooks

Each task runs in its own process, and `session.start()` returns while the tasks keep running. In a notebook, the cell can therefore finish before any results are printed.

To wait for the tasks to finish, join their processes after starting the session:

```py
import multiprocessing

session = Session(tasks=[task]).start()

# Only needed in Jupyter notebooks: wait for the tasks, so their results appear in the notebook
for process in multiprocessing.active_children():
    process.join()
```

`active_children()` returns every child process started from the notebook, so this also waits for any other child processes running in the same kernel.

Tasks reading a stream that never ends keep running until they are stopped. To stop them, call:

```py
session.gracefully_kill(timeout_seconds=5)
```
