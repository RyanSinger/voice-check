# Voice Check Examples

Before/after examples for each rule category. Use these to calibrate when fixing violations.

## Hard rules

### No dashes
- BEFORE: "The plan is simple, ship the MVP first, polish later."
- AFTER: "The plan is simple. Ship the MVP first, polish later."

### No hedging
- BEFORE: "I would like to potentially take on the auth refactor."
- AFTER: "I'm taking the auth refactor."

### No copula avoidance
- BEFORE: "This document serves as a record of the meeting."
- AFTER: "This document is a record of the meeting."

## AI vocabulary cluster

- BEFORE: "The pivotal shift in our approach underscores the crucial need to leverage these enduring patterns."
- AFTER: "We changed our approach because these patterns work."

## Puffery and significance

- BEFORE: "This represents a groundbreaking shift in how we think about deployment."
- AFTER: "We deploy differently now: every push goes to staging in under 30 seconds."

## Dangling participles

- BEFORE: "The team shipped the feature, highlighting the importance of cross-functional collaboration."
- AFTER: "The team shipped the feature. Eng, design, and product reviewed every PR."

## Promotional tone

- BEFORE: "Nestled in the heart of the trading floor, our system boasts vibrant real-time dashboards."
- AFTER: "The system runs on the trading floor with real-time dashboards."

## Structural tells

### Rule of three
- BEFORE: "We need speed, accuracy, and reliability."
- AFTER: "We need speed and accuracy. Reliability comes from those two."

### Negative parallelism
- BEFORE: "It's not just a tool, it's a workflow."
- AFTER: "It's a workflow."

### False ranges
- BEFORE: "From hobbyists to enterprise, our users span the spectrum."
- AFTER: "Most users are hobbyists. We have a few enterprise contracts."

### Challenges and future prospects
- BEFORE: "Despite its strong adoption, the framework faces challenges, but the team remains optimistic about future growth."
- AFTER: "Adoption is strong. The team is fixing the slow build problem next quarter."

### Elegant variation
- BEFORE: "Nick led the project. The engineer brought deep expertise. The technical lead's experience showed."
- AFTER: "Nick led the project. Nick has deep expertise. It showed."

## Vague attributions

- BEFORE: "Industry observers note that this approach is gaining traction."
- AFTER: "Stripe's engineering blog described this approach in February. Linear and Vercel adopted it the same month."
