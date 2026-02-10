# Diagram Patterns Reference

Common Mermaid diagram patterns for code explanations.

## API Handler / Request Pipeline

```mermaid
flowchart TD
    A[HTTP Request] --> B[Middleware]
    B --> C[Auth Check]
    C -->|Pass| D[Route Handler]
    C -->|Fail| E[401 Response]
    D --> F[Business Logic]
    F --> G[Database Query]
    G --> H[Response Builder]
    H --> I[HTTP Response]
```

## Class Hierarchy

```mermaid
classDiagram
    class BaseClass {
        +method_a()
        +method_b()
        #internal_state
    }
    class ConcreteA {
        +method_a()
    }
    class ConcreteB {
        +method_a()
        +extra_method()
    }
    BaseClass <|-- ConcreteA
    BaseClass <|-- ConcreteB
```

## Event-Driven Flow

```mermaid
sequenceDiagram
    participant Producer
    participant Queue
    participant Consumer
    participant Store

    Producer->>Queue: emit(event)
    Queue->>Consumer: deliver(event)
    Consumer->>Consumer: process(event)
    Consumer->>Store: save(result)
    Consumer-->>Queue: ack()
```

## State Machine

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Processing : start()
    Processing --> Success : complete()
    Processing --> Error : fail()
    Error --> Idle : retry()
    Success --> [*]
```

## Pipeline / Data Transformation

```mermaid
graph LR
    A[Raw Input] --> B[Parse]
    B --> C[Validate]
    C --> D[Transform]
    D --> E[Enrich]
    E --> F[Output]

    C -->|Invalid| G[Error Log]
```

## Dependency Graph

```mermaid
graph TD
    A[Module A] --> B[Module B]
    A --> C[Module C]
    B --> D[Shared Utils]
    C --> D
    C --> E[External API]
```

## Decision Tree

```mermaid
flowchart TD
    A{Input Type?}
    A -->|String| B[Parse String]
    A -->|Number| C[Validate Range]
    A -->|Object| D[Extract Fields]
    B --> E{Valid Format?}
    E -->|Yes| F[Process]
    E -->|No| G[Reject]
    C --> F
    D --> F
```

## Choosing the Right Diagram

| Scenario | Diagram Type |
|----------|-------------|
| Function calls between components | sequenceDiagram |
| Decision logic, branching | flowchart TD |
| Data transformation pipeline | graph LR |
| Class/interface relationships | classDiagram |
| Object lifecycle states | stateDiagram-v2 |
| Module dependencies | graph TD |
| Concurrent/parallel flows | sequenceDiagram with par blocks |
