"""Deterministic priority scheduler with cancellation and bounded retries."""

from __future__ import annotations

import heapq
from dataclasses import replace
from datetime import datetime
from threading import RLock
from typing import Dict, List, Optional, Set, Tuple

from ..clock import Clock, SystemClock
from ..errors import DuplicateRequestError, ValidationError
from ..validation import aware_time, integer_value
from .jobs import Job, JobRun, JobStatus


class JobScheduler:
    def __init__(self, *, clock: Optional[Clock] = None) -> None:
        self.clock = clock or SystemClock()
        self._jobs: Dict[str, Job] = {}
        self._queue: List[Tuple[datetime, int, str]] = []
        self._attempts: Dict[str, int] = {}
        self._cancelled: Set[str] = set()
        self._runs: List[JobRun] = []
        self._counter = 0
        self._lock = RLock()

    def schedule(self, job: Job) -> Job:
        if not isinstance(job, Job):
            raise ValidationError("job must be a Job")
        with self._lock:
            if job.job_id in self._jobs:
                raise DuplicateRequestError("job id already exists")
            self._jobs[job.job_id] = job
            self._enqueue(job)
            return job

    def _enqueue(self, job: Job) -> None:
        self._counter += 1
        heapq.heappush(self._queue, (job.run_at, self._counter, job.job_id))

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            if job_id not in self._jobs or job_id in self._cancelled:
                return False
            self._cancelled.add(job_id)
            return True

    def reschedule(self, job_id: str, run_at: datetime) -> Job:
        checked = aware_time(run_at, "run_at")
        with self._lock:
            try:
                current = self._jobs[job_id]
            except KeyError:
                raise KeyError("unknown job %s" % job_id)
            if job_id in self._cancelled:
                raise ValidationError("cancelled jobs cannot be rescheduled")
            updated = replace(current, run_at=checked)
            self._jobs[job_id] = updated
            self._enqueue(updated)
            return updated

    def run_due(self, at: Optional[datetime] = None, *, maximum: int = 100) -> Tuple[JobRun, ...]:
        current = aware_time(at, "at") if at is not None else self.clock.now()
        limit = integer_value(maximum, "maximum", minimum=1, maximum=10000)
        completed: List[JobRun] = []
        with self._lock:
            while self._queue and len(completed) < limit:
                run_at, _, job_id = self._queue[0]
                if run_at > current:
                    break
                heapq.heappop(self._queue)
                job = self._jobs.get(job_id)
                if job is None or job_id in self._cancelled or job.run_at != run_at:
                    continue
                completed.append(self._execute(job, current))
        return tuple(completed)

    def _execute(self, job: Job, current: datetime) -> JobRun:
        attempt = self._attempts.get(job.job_id, 0) + 1
        self._attempts[job.job_id] = attempt
        started = self.clock.now()
        try:
            result = job.handler(job.payload)
        except Exception as exc:
            finished = self.clock.now()
            run = JobRun(
                job.job_id,
                attempt,
                JobStatus.FAILED,
                started,
                finished,
                error="%s: %s" % (exc.__class__.__name__, exc),
            )
            if attempt < job.retry_policy.attempts:
                retry_at = finished + job.retry_policy.delay_after(attempt)
                replacement = replace(job, run_at=retry_at)
                self._jobs[job.job_id] = replacement
                self._enqueue(replacement)
        else:
            run = JobRun(
                job.job_id,
                attempt,
                JobStatus.SUCCEEDED,
                started,
                self.clock.now(),
                result=result,
            )
        self._runs.append(run)
        return run

    def next_run_at(self) -> Optional[datetime]:
        with self._lock:
            while self._queue:
                run_at, _, job_id = self._queue[0]
                job = self._jobs.get(job_id)
                if job is None or job_id in self._cancelled or job.run_at != run_at:
                    heapq.heappop(self._queue)
                    continue
                return run_at
            return None

    def runs(self, job_id: Optional[str] = None) -> Tuple[JobRun, ...]:
        with self._lock:
            return tuple(
                run for run in self._runs if job_id is None or run.job_id == job_id
            )

    def pending(self) -> Tuple[Job, ...]:
        with self._lock:
            return tuple(
                sorted(
                    (
                        job
                        for key, job in self._jobs.items()
                        if key not in self._cancelled
                        and not any(
                            run.job_id == key and run.status is JobStatus.SUCCEEDED
                            for run in self._runs
                        )
                    ),
                    key=lambda job: (job.run_at, job.job_id),
                )
            )
