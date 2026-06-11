package com.rag.gateway.mcp;

import com.rag.gateway.dto.ApiResponse;
import com.rag.gateway.model.AgentTrace;
import com.rag.gateway.repository.pg.TraceMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

@Component
public class AuditToolHandler {

    private static final Logger log = LoggerFactory.getLogger(AuditToolHandler.class);
    private final TraceMapper traceMapper;

    public AuditToolHandler(TraceMapper traceMapper) {
        this.traceMapper = traceMapper;
    }

    public ApiResponse<?> auditLog(Map<String, Object> body) {
        String eventType = (String) body.get("event_type");
        String userId = (String) body.get("user_id");
        @SuppressWarnings("unchecked")
        Map<String, Object> detail = (Map<String, Object>) body.getOrDefault("detail", new HashMap<>());

        log.info("AUDIT [{}] user={} detail={}", eventType, userId, detail);

        // Persist agent_trace events to PG
        if ("agent_trace".equals(eventType)) {
            persistTrace(userId, detail);
        }

        Map<String, Object> result = new HashMap<>();
        result.put("ack", true);
        return ApiResponse.success(result);
    }

    private void persistTrace(String userId, Map<String, Object> detail) {
        try {
            AgentTrace trace = new AgentTrace();
            trace.setRequestId((String) detail.getOrDefault("request_id", ""));
            trace.setUserId(userId);
            trace.setSessionId((String) detail.getOrDefault("session_id", ""));
            trace.setQuery((String) detail.getOrDefault("query", ""));
            trace.setGate(toJsonString(detail.get("gate")));
            trace.setRetrieval(toJsonString(detail.get("retrieval")));
            trace.setGeneration(toJsonString(detail.get("generation")));
            trace.setVerification(toJsonString(detail.get("verification")));
            trace.setTotalLatencyMs(toDouble(detail.get("total_latency_ms")));
            traceMapper.insert(trace);
        } catch (Exception e) {
            log.warn("Failed to persist agent_trace: {}", e.getMessage());
        }
    }

    private static String toJsonString(Object obj) {
        if (obj == null) return "{}";
        if (obj instanceof String) return (String) obj;
        // Map or other objects — Jackson not available, use simple toString fallback
        return obj.toString();
    }

    private static Double toDouble(Object obj) {
        if (obj == null) return 0.0;
        if (obj instanceof Number) return ((Number) obj).doubleValue();
        try { return Double.parseDouble(obj.toString()); } catch (Exception e) { return 0.0; }
    }
}