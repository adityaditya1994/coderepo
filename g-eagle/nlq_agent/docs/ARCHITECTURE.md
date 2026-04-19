# Multi-Agent Architecture

```mermaid
graph TD

    %% Common styles
    classDef agent fill:#1a365d,stroke:#2b6cb0,stroke-width:2px,color:#fff;
    classDef internal fill:#2d3748,stroke:#4a5568,color:#edf2f7;
    classDef memory fill:#2c7a7b,stroke:#319795,color:#fff;
    classDef llm fill:#7b341e,stroke:#c53030,color:#fff;
    
    %% User Input
    User((User Request)) --> SupervisorAgent

    %% 1. Supervisor
    subgraph SupervisorAgent [Supervisor Agent]
        direction TB
        S_Input[Receive NL Query]:::internal --> S_Route[Route / Validate Intent]:::internal
    end

    SupervisorAgent --> DiscoveryAgent

    %% 2. Discovery
    subgraph DiscoveryAgent [Discovery Agent]
        direction TB
        D_Input[Query & Metadata Context]:::internal --> D_Search{Parallel Search}:::internal
        D_Search --> FlatFile[FlatFile Connector]:::internal
        D_Search --> GlueData[AWS Glue Catalogs]:::internal
        D_Search --> VectorDB[Pinecone Vetor Search]:::internal
        
        FlatFile --> Council
        GlueData --> Council
        VectorDB --> Council
        
        Council[Discovery Council]:::llm --> TopK[Select Top K Tables]:::internal
    end

    DiscoveryAgent --> SchemaRetrieverAgent

    %% 3. Schema Retriever
    subgraph SchemaRetrieverAgent [Schema Retriever Agent]
        direction TB
        SR_Input[Top K Tables]:::internal --> SR_Target{Target Config}:::internal
        SR_Target --> SR_Glue[AWS Glue Schema]:::internal
        SR_Target --> SR_PG[Postgres info_schema]:::internal
        SR_Glue --> SR_Merge[Merge Full Columns + Types]:::internal
        SR_PG --> SR_Merge
    end

    SchemaRetrieverAgent --> QueryPlannerAgent

    %% 4. Query Planner
    subgraph QueryPlannerAgent [Query Planner Agent]
        direction TB
        QP_Input[Query + Schemas]:::internal --> QP_Rules[Apply Join Rules & Filters]:::internal
        QP_Rules --> QP_LLM[LLM Planner]:::llm
        QP_LLM --> QP_JSON[Structured Query Plan JSON]:::internal
    end

    QueryPlannerAgent --> SqlGeneratorAgent

    %% 5. SQL Generator
    subgraph SqlGeneratorAgent [SQL Generator Agent]
        direction TB
        SG_Input[Query Plan JSON]:::internal --> SG_Dialect[Determine SQL Dialect]:::internal
        SG_Dialect --> SG_LLM[LLM SQL Writer]:::llm
        SG_LLM --> SG_Clean[Clean Executable SQL]:::internal
    end

    SqlGeneratorAgent --> ExecutorAgent

    %% 6. Executor
    subgraph ExecutorAgent [Database Executor Agent]
        direction TB
        EX_Input[Raw SQL]:::internal --> EX_Factory{DB Factory}:::internal
        EX_Factory --> Athena[AWS Athena]:::internal
        EX_Factory --> Postgres[Local Postgres]:::internal
        Athena --> EX_Result[Result / Error Capture]:::internal
        Postgres --> EX_Result
        EX_Result --> RetryCtrl[Increment Retry Count]:::internal
    end

    ExecutorAgent --> ValidatorAgent

    %% 7. Validator Council
    subgraph ValidatorAgent [Validation Council Agent]
        direction TB
        VA_Input[SQL + Result]:::internal --> VA_Parallel{Run Validators}:::internal
        
        VA_Parallel --> V_Schema[Schema Rule Validator]:::internal
        VA_Parallel --> V_Data[Data Sanity Validator]:::internal
        VA_Parallel --> V_Logic[Logic Validator LLM]:::llm
        VA_Parallel --> V_Bus[Business/Metric Validator LLM]:::llm
        
        V_Schema --> V_Agg
        V_Data --> V_Agg
        V_Logic --> V_Agg
        V_Bus --> V_Agg
        
        V_Agg[Aggregate Score]:::internal --> V_Rec[Retry | Proceed | Escalate]:::internal
    end

    %% Retry Loop / SQL Fixer
    subgraph SqlFixerAgent [SQL Fixer Agent]
        direction TB
        F_Input[Execution Error / Validator Feedback]:::internal --> F_LLM[LLM SQL Patcher]:::llm
        F_LLM --> F_Out[Repaired SQL]:::internal
    end

    %% Routing logic from Validator
    ValidatorAgent -.->|Retry| SqlFixerAgent
    SqlFixerAgent -.->|Loop| ExecutorAgent
    
    ValidatorAgent -.->|Escalate| HumanHandoffAgent
    ValidatorAgent -.->|Proceed| SummarizerAgent

    %% 8. Human Handoff
    subgraph HumanHandoffAgent [Human Handoff Agent]
        direction TB
        HH_Input[Low Confidence / Max Retries]:::internal --> HH_Fmt[Format Rescue Package]:::internal
    end

    %% 9. Summarizer
    subgraph SummarizerAgent [Summarizer Agent]
        direction TB
        SM_Input[SQL Results + Query]:::internal --> SM_LLM[LLM Narrative Gen]:::llm
        SM_LLM --> SM_Out[Final Natural Language Answer]:::internal
    end

    %% 10. Memory Writer (Runs after terminal nodes)
    subgraph MemorySystem [Memory Manager System]
        direction LR
        Mem_Context[Memory Writer Extractor]:::internal --> Mem_Short[Short-Term Session]:::memory
        Mem_Context --> Mem_Long[Long-Term SQLite]:::memory
        Mem_Context --> Mem_Sem[Semantic Vector DB]:::memory
    end

    SummarizerAgent --> MemorySystem
    HumanHandoffAgent --> MemorySystem
    MemorySystem --> Output((Final Answer / UI))

```
