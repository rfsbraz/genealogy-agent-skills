# Everyday research flow

Start with a person, a question or a document. The agent either discovers sources, reads supplied material or resumes the saved next step. It saves evidence and uncertainty, then evaluates the five GPS elements before accepting a conclusion. If the evidence is incomplete, it preserves a working lead and chooses the next useful action. The user receives a short finding with citations; the complete audit remains available.

```mermaid
flowchart TD
  A["Person, question or document"] --> B{"What is needed?"}
  B -->|Research| C["Find relevant sources"]
  B -->|Read| D["Quick or detailed reading"]
  B -->|Continue| E["Resume saved work"]
  C --> D
  E --> F["Next useful action"]
  F --> C
  D --> G["Save evidence and uncertainty"]
  G --> H{"All five GPS elements met?"}
  H -->|Yes| I["Reviewed conclusion"]
  H -->|No| J["Working lead and next step"]
  J --> F
  I --> K["Brief finding with citations"]
```
