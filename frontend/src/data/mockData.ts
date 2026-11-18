import type { ResumeData, ProficiencyLevel } from '../types';

export const DEMO_USER = {
  name: 'Alex Morgan',
  email: 'demo.candidate@example.com',
  password: 'Password123!',
  role: 'Senior Software Engineer'
};

export const SAMPLE_RESUMES: Record<string, ResumeData> = {
  fullstack: {
    fileName: 'Alex_Morgan_Backend_Resume.pdf',
    candidateName: 'Alex Morgan',
    title: 'Senior Python & Distributed Systems Engineer',
    experienceYears: 5,
    extractedSkills: [
      'Python',
      'FastAPI',
      'PostgreSQL',
      'Docker',
      'Redis',
      'AsyncIO',
      'LiveKit',
      'FastMCP',
      'Kubernetes'
    ],
    summary: 'Senior Backend Engineer specializing in high-throughput real-time voice architectures, async event-driven microservices, and FastMCP integration.'
  },
  aiml: {
    fileName: 'Alex_Morgan_AI_ML_Resume.pdf',
    candidateName: 'Alex Morgan',
    title: 'AI/ML Systems & Voice Engineer',
    experienceYears: 4,
    extractedSkills: [
      'Python',
      'PyTorch',
      'LangChain',
      'RAG',
      'Silero VAD',
      'ONNX Runtime',
      'Vector Databases',
      'FastAPI'
    ],
    summary: 'Applied Machine Learning Engineer focused on low-latency voice AI agents, speech-to-text endpointing, Silero VAD tuning, and LLM guardrails.'
  }
};

export interface QuestionBankItem {
  id: number;
  question: string;
  followUp: string;
  topic: string;
}

export const QUESTION_BANK: Record<string, Record<ProficiencyLevel, QuestionBankItem[]>> = {
  Python: {
    Beginner: [
      {
        id: 1,
        question: "Could you explain the difference between mutable and immutable data types in Python, and give an example of each?",
        followUp: "What happens if you pass a mutable object like a list as a default argument in a function?",
        topic: "Data Structures & Mutability"
      },
      {
        id: 2,
        question: "How does error handling work with try, except, else, and finally blocks in Python?",
        followUp: "When would you prefer catching a specific exception over a generic Exception?",
        topic: "Exception Handling"
      },
      {
        id: 3,
        question: "What are list comprehensions in Python, and when might a standard for loop be preferable?",
        followUp: "How do list comprehensions differ in memory usage compared to generator expressions?",
        topic: "Syntax & Performance"
      }
    ],
    Intermediate: [
      {
        id: 1,
        question: "How does Python's AsyncIO event loop manage concurrent coroutines, and how does it differ from multithreading?",
        followUp: "What happens when you call a blocking synchronous library inside an async function?",
        topic: "AsyncIO & Concurrency"
      },
      {
        id: 2,
        question: "Can you explain how decorators work in Python and how you would build a decorator that accepts custom arguments?",
        followUp: "Why is `functools.wraps` important when defining custom decorators?",
        topic: "Metaprogramming & Closures"
      },
      {
        id: 3,
        question: "How does Python's memory management and garbage collector handle reference counting and cyclic references?",
        followUp: "How does the generational garbage collection algorithm detect unreachable cycles?",
        topic: "Memory Management & GC"
      }
    ],
    Expert: [
      {
        id: 1,
        question: "Under Python's Global Interpreter Lock (GIL), how do you design a real-time system that handles CPU-intensive workloads alongside high-throughput I/O without blocking the asyncio loop?",
        followUp: "With PEP 703 free-threaded Python (no-GIL), what concurrency bugs and data race hazards must backend engineers now guard against?",
        topic: "GIL Internals & Multi-Core Concurrency"
      },
      {
        id: 2,
        question: "In distributed microservices using FastMCP and asyncio, how do you prevent cascading event-loop starvation when external downstream tool calls experience high latency spikes?",
        followUp: "What circuit breaker and bounded semaphore patterns do you implement to enforce deterministic SLA latency bounds?",
        topic: "FastMCP & Resilient Microservice Architecture"
      },
      {
        id: 3,
        question: "How does Python construct class instances via __new__ versus __init__, and how would you implement a metaclass or custom descriptor to enforce runtime schema validation?",
        followUp: "How do descriptors interact with __getattribute__ and the instance __dict__ lookup chain?",
        topic: "Metaclasses, Descriptors & Internals"
      }
    ]
  },
  'C++': {
    Beginner: [
      {
        id: 1,
        question: "Can you explain how memory management and pointers work in C++ compared to references?",
        followUp: "What is the difference between stack and heap memory allocation in C++?",
        topic: "Pointers & Memory"
      },
      {
        id: 2,
        question: "What are classes and constructors in C++, and what is the role of a destructor?",
        followUp: "Why should a base class destructor almost always be declared virtual?",
        topic: "OOP & Destructors"
      },
      {
        id: 3,
        question: "What is the Standard Template Library (STL) and how do std::vector and std::array differ?",
        followUp: "How does std::vector manage dynamic capacity reallocation under the hood?",
        topic: "STL Containers"
      }
    ],
    Intermediate: [
      {
        id: 1,
        question: "What are smart pointers in modern C++, specifically std::unique_ptr and std::shared_ptr?",
        followUp: "How does std::weak_ptr prevent cyclic reference memory leaks in std::shared_ptr graphs?",
        topic: "Modern C++ Smart Pointers"
      },
      {
        id: 2,
        question: "Can you explain RAII (Resource Acquisition Is Initialization) and why it is foundational to exception safety in C++?",
        followUp: "What are the three exception safety guarantees in C++ (basic, strong, no-throw)?",
        topic: "RAII & Exception Safety"
      },
      {
        id: 3,
        question: "How do rvalue references and move semantics (std::move) optimize performance in C++11 and beyond?",
        followUp: "What is the Rule of 5 in modern C++ and when do you need to implement it?",
        topic: "Move Semantics & Rule of 5"
      }
    ],
    Expert: [
      {
        id: 1,
        question: "How does the C++ memory model define atomics, memory orders, and happens-before relationships in lock-free concurrency?",
        followUp: "How do you avoid false sharing and cache-line bouncing in high-throughput lock-free queues?",
        topic: "Lock-Free Concurrency"
      },
      {
        id: 2,
        question: "Can you explain template metaprogramming, SFINAE, and how C++20 Concepts simplify template constraints?",
        followUp: "How does constexpr and consteval evaluation differ from compile-time template instantiation?",
        topic: "Concepts & Metaprogramming"
      },
      {
        id: 3,
        question: "How do C++ compilers implement virtual method tables (vtables), and what is the exact runtime memory overhead of virtual inheritance?",
        followUp: "How does devirtualization optimization work in modern optimizing compilers?",
        topic: "Vtable Internals & Memory Layout"
      }
    ]
  },
  FastAPI: {
    Beginner: [
      {
        id: 1,
        question: "What is FastAPI, and how does it use Pydantic models for request validation?",
        followUp: "How does FastAPI automatically generate OpenAPI interactive Swagger documentation?",
        topic: "Basics & Pydantic"
      },
      {
        id: 2,
        question: "How do path parameters and query parameters differ in FastAPI route definitions?",
        followUp: "How do you define optional query parameters with default values?",
        topic: "Routing"
      },
      {
        id: 3,
        question: "How do you return custom HTTP status codes and responses in FastAPI endpoints?",
        followUp: "What exception do you raise to return an HTTP 404 or 400 error?",
        topic: "HTTP Responses"
      }
    ],
    Intermediate: [
      {
        id: 1,
        question: "How does FastAPI's Dependency Injection system (`Depends`) work, and how can it manage database session lifetimes?",
        followUp: "How do `yield` dependencies ensure cleanup and rollback on unhandled errors?",
        topic: "Dependency Injection"
      },
      {
        id: 2,
        question: "How does FastAPI execute endpoints declared with `async def` versus standard `def`?",
        followUp: "Why does declaring a blocking I/O operation in `async def` hurt performance more than in `def`?",
        topic: "Async vs Threadpool Execution"
      },
      {
        id: 3,
        question: "How do you implement authentication middleware or OAuth2 password bearer tokens in FastAPI?",
        followUp: "Where should JWT token validation occur for maximum performance and security?",
        topic: "Security & Auth"
      }
    ],
    Expert: [
      {
        id: 1,
        question: "In high-throughput FastAPI microservices serving 10,000+ WebSocket audio streaming connections, how do you architect connection pooling, backpressure, and heartbeat monitoring?",
        followUp: "How do you decouple websocket message processing from ASGI worker event loops using Redis pub/sub?",
        topic: "Real-time WebSockets at Scale"
      },
      {
        id: 2,
        question: "How do you optimize Uvicorn ASGI worker configurations with uvloop and httptools in Kubernetes environments under high concurrency?",
        followUp: "How do you gracefully handle SIGTERM to drain in-flight audio streaming requests without dropping packets?",
        topic: "ASGI Internals & K8s Lifecycle"
      },
      {
        id: 3,
        question: "How do you construct custom ASGI middleware to intercept streaming payloads, inject distributed tracing span headers (OpenTelemetry), and enforce rate limiting without buffering full request bodies in memory?",
        followUp: "How do you handle streaming responses when downstream clients disconnect prematurely?",
        topic: "Streaming Middleware & Distributed Tracing"
      }
    ]
  },
  Docker: {
    Beginner: [
      {
        id: 1,
        question: "What is the primary difference between a Docker image and a Docker container?",
        followUp: "How does containerization differ from traditional virtual machines?",
        topic: "Container Fundamentals"
      },
      {
        id: 2,
        question: "What are the common instructions used in a Dockerfile like FROM, WORKDIR, COPY, and CMD?",
        followUp: "What is the difference between CMD and ENTRYPOINT?",
        topic: "Dockerfile Basics"
      },
      {
        id: 3,
        question: "How do Docker volumes enable data persistence across container restarts?",
        followUp: "What is the difference between a named volume and a bind mount?",
        topic: "Storage & Persistence"
      }
    ],
    Intermediate: [
      {
        id: 1,
        question: "How do multi-stage Docker builds reduce the final image size and improve security?",
        followUp: "Why should you never leave build tools and package caches inside production image layers?",
        topic: "Multi-stage Builds & Optimization"
      },
      {
        id: 2,
        question: "How do Docker bridge and overlay networks function, and how do containers resolve each other by name?",
        followUp: "How does Docker's embedded DNS server handle service discovery within a custom bridge network?",
        topic: "Container Networking"
      },
      {
        id: 3,
        question: "How do you securely pass secrets and environment variables to containers without baking them into Docker images?",
        followUp: "Why is copying a `.env` file into a Dockerfile build layer dangerous?",
        topic: "Secrets Management"
      }
    ],
    Expert: [
      {
        id: 1,
        question: "How do Linux cgroups (v2) and namespaces (PID, NET, IPC, MNT, USER) provide isolation, and how do you configure resource quotas to prevent noisy-neighbor CPU throttling?",
        followUp: "How does CFS (Completely Fair Scheduler) quota allocation affect Python async event loops inside containers?",
        topic: "Kernel Namespaces & Cgroups v2"
      },
      {
        id: 2,
        question: "How do rootless containers and user namespaces prevent privilege escalation attacks in multi-tenant container platforms?",
        followUp: "What limitations do rootless containers face regarding port binding under 1024 and storage drivers?",
        topic: "Container Hardening & Rootless Execution"
      },
      {
        id: 3,
        question: "How do you troubleshoot low-level container networking issues like MTU mismatch or socket connection dropouts in Kubernetes overlay networks?",
        followUp: "How would you use eBPF or tcpdump within a network namespace without altering container binaries?",
        topic: "Low-level Networking & Observability"
      }
    ]
  }
};
