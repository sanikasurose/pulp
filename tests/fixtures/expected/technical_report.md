Performance Optimisation Report
System: Order Processing Service | Date: March 2026 | Author: Engineering Team
1. Executive Summary
This report documents the results of a three-week performance optimisation effort on the Order Processing
Service. The primary bottleneck was identified as synchronous database calls within the request path. By introducing connection pooling, query batching, and an in-process LRU cache for read-heavy endpoints, throughput increased by 187% while p99 latency dropped from 310ms to 95ms.
2. Results Summary
Metric Baseline Optimised Delta
Throughput (req/s) 1,200 3,450 +187% p50 latency (ms) 42 18 -57% p99 latency (ms) 310 95 -69%
Error rate (%) 0.8 0.1 -87%
CPU usage (%) 78 45 -42%
Memory (MB RSS) 640 390 -39%
3. Methodology
All measurements were taken on production hardware during a low-traffic window (02:00–04:00 UTC). Load was generated using k6 with a constant arrival rate of 2,000 virtual users. Results were averaged over three
10-minute runs per configuration. The baseline configuration was the unmodified release tagged v2.3.1.
4. Conclusions
The optimised build is ready for gradual rollout. A feature flag controls the new connection pool size.
Recommend 10% canary for 48 hours before full rollout. Monitoring dashboards have been updated to track the new latency SLOs.
