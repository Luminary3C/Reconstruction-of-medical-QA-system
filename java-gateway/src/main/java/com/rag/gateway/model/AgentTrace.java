package com.rag.gateway.model;

import java.time.LocalDateTime;

public class AgentTrace {
    private Long id;
    private String requestId;
    private String userId;
    private String sessionId;
    private String query;
    private String gate;
    private String retrieval;
    private String generation;
    private String verification;
    private Double totalLatencyMs;
    private LocalDateTime createdAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getRequestId() { return requestId; }
    public void setRequestId(String requestId) { this.requestId = requestId; }
    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }
    public String getSessionId() { return sessionId; }
    public void setSessionId(String sessionId) { this.sessionId = sessionId; }
    public String getQuery() { return query; }
    public void setQuery(String query) { this.query = query; }
    public String getGate() { return gate; }
    public void setGate(String gate) { this.gate = gate; }
    public String getRetrieval() { return retrieval; }
    public void setRetrieval(String retrieval) { this.retrieval = retrieval; }
    public String getGeneration() { return generation; }
    public void setGeneration(String generation) { this.generation = generation; }
    public String getVerification() { return verification; }
    public void setVerification(String verification) { this.verification = verification; }
    public Double getTotalLatencyMs() { return totalLatencyMs; }
    public void setTotalLatencyMs(Double totalLatencyMs) { this.totalLatencyMs = totalLatencyMs; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
