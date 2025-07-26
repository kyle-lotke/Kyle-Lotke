# Architecture Overview

Below is the high-level diagram of the agent components:

![Agent Architecture](architecture-diagram.png)

## Components
 [Download Demo Sheet (PDF)](projectscope.pdf)
1. **User Interface**  
   - Triggered via email
   - AI call to ensure it is about gorilla hike assignment, disregards if not 

2. **Agent Core**  
   - **Parser**: Complex multi Agent parser to collect daily instructured gorilla location/hike difficulty and daily unstrcure tourist hike requests  
   - **Optimizer**: Both AI powered parsed request and hike data fed into local optimization file through personal api connection. The optimizer then picks the optimal combonations of tourists per gorilla family. Then the api sends the results out to the agent who sends it back to the original email
   - **Memory**: Lightweight structured output parsers with custom error catching loops to store mistakes in memory and adapt 

3. **Tools / APIs**  
   - Gurobi solver via Python  
   - n8n integrations (Google Sheets, Email, HTTP)  
   - Optional terrain parser for hike features  

4. **Observability**  
   - Logs every assignment to `logs/` folder  
   - Handles malformed inputs and retries failed optimizations  
