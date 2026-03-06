"""
Host and Container Telemetry Endpoints

Provides real-time system metrics for the Dashboard:
- Host system stats (CPU, memory, disk)
- Aggregate container stats across all running agents
"""

import asyncio
import psutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException

from services.docker_service import docker_client, list_all_agents_fast

# Module-level executor for Docker operations (blocking calls)
# Limited to 4 workers to avoid overwhelming Docker daemon
_docker_executor = ThreadPoolExecutor(max_workers=4)

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])

# Initialize CPU percent tracking (first call with interval=None returns 0)
# This primes the counter so subsequent calls return meaningful values
psutil.cpu_percent(interval=None)


@router.get("/host")
async def get_host_stats():
    """
    Get host system statistics using psutil.

    Returns CPU, memory, and disk usage metrics.
    No authentication required (follows OTel pattern).
    """
    try:
        # CPU - use interval=None to get last computed value (non-blocking)
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_count = psutil.cpu_count()

        # Memory
        mem = psutil.virtual_memory()

        # Disk - use root partition
        disk = psutil.disk_usage('/')

        return {
            "cpu": {
                "percent": round(cpu_percent, 1),
                "count": cpu_count
            },
            "memory": {
                "percent": round(mem.percent, 1),
                "used_gb": round(mem.used / (1024**3), 1),
                "total_gb": round(mem.total / (1024**3), 1)
            },
            "disk": {
                "percent": round(disk.percent, 1),
                "used_gb": round(disk.used / (1024**3), 1),
                "total_gb": round(disk.total / (1024**3), 1)
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting host stats: {str(e)}")


def _get_single_container_stats_sync(agent_name: str) -> Dict[str, Any]:
    """
    Synchronous helper to get stats for a single container.
    Runs in thread pool to avoid blocking the event loop.
    """
    try:
        container = docker_client.containers.get(f"agent-{agent_name}")

        # Get stats (one-shot) - this is the blocking call (~1-2s per container)
        stats = container.stats(stream=False)

        # Calculate CPU percentage
        cpu_percent = 0.0
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                   stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                      stats['precpu_stats']['system_cpu_usage']

        if system_delta > 0 and cpu_delta > 0:
            num_cpus = len(stats['cpu_stats']['cpu_usage'].get('percpu_usage', [])) or 1
            cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0

        # Get memory usage (subtract cache for accuracy)
        memory_usage = stats['memory_stats'].get('usage', 0)
        memory_cache = stats['memory_stats'].get('stats', {}).get('cache', 0)
        memory_used = memory_usage - memory_cache
        memory_mb = round(memory_used / (1024 * 1024), 1)

        return {
            "name": agent_name,
            "cpu": round(cpu_percent, 1),
            "memory_mb": memory_mb
        }

    except Exception as e:
        return {
            "name": agent_name,
            "cpu": 0,
            "memory_mb": 0,
            "error": str(e)
        }


@router.get("/containers")
async def get_container_stats():
    """
    Get aggregate statistics across all running agent containers.

    Returns total CPU usage, memory consumption, and per-container breakdown.
    Uses parallel execution for better performance with multiple containers.
    No authentication required (follows OTel pattern).
    """
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker not available")

    try:
        # Get all running agent containers - use fast version (only need names)
        agents = list_all_agents_fast()
        running_agents = [a for a in agents if a.status == "running"]

        if not running_agents:
            return {
                "running_count": 0,
                "total_cpu_percent": 0,
                "total_memory_mb": 0,
                "containers": [],
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

        # Fetch all container stats in PARALLEL using thread pool
        # This reduces time from O(n * 1-2s) to O(1-2s) for n containers
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(_docker_executor, _get_single_container_stats_sync, agent.name)
            for agent in running_agents
        ]

        # Wait for all stats to complete concurrently
        containers_stats = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results, handling any exceptions
        processed_stats: List[Dict[str, Any]] = []
        total_cpu_percent = 0.0
        total_memory_mb = 0

        for result in containers_stats:
            if isinstance(result, Exception):
                # Unlikely, but handle gracefully
                continue
            if isinstance(result, dict):
                processed_stats.append(result)
                if "error" not in result:
                    total_cpu_percent += result.get("cpu", 0)
                    total_memory_mb += result.get("memory_mb", 0)

        return {
            "running_count": len(running_agents),
            "total_cpu_percent": round(total_cpu_percent, 1),
            "total_memory_mb": round(total_memory_mb, 1),
            "containers": sorted(processed_stats, key=lambda x: x.get('cpu', 0), reverse=True),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting container stats: {str(e)}")
