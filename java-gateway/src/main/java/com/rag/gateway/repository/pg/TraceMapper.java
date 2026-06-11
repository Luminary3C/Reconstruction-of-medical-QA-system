package com.rag.gateway.repository.pg;

import com.rag.gateway.model.AgentTrace;
import org.apache.ibatis.annotations.*;

@Mapper
public interface TraceMapper {

    @Insert("INSERT INTO agent_traces (request_id, user_id, session_id, query, " +
            "gate, retrieval, generation, verification, total_latency_ms, created_at) " +
            "VALUES (#{requestId}, #{userId}, #{sessionId}, #{query}, " +
            "#{gate}::jsonb, #{retrieval}::jsonb, #{generation}::jsonb, #{verification}::jsonb, " +
            "#{totalLatencyMs}, NOW())")
    int insert(AgentTrace trace);
}