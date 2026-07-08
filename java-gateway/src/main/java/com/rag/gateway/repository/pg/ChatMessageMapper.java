package com.rag.gateway.repository.pg;

import com.rag.gateway.model.ChatMessage;
import com.rag.gateway.dto.SessionSummary;
import org.apache.ibatis.annotations.*;

import java.util.List;

@Mapper
public interface ChatMessageMapper {

    @Insert("INSERT INTO chat_messages (user_id, session_id, question, answer, embedding, created_at) " +
            "VALUES (#{userId}, #{sessionId}, #{question}, #{answer}, #{embedding}::vector, NOW())")
    int insertWithEmbedding(@Param("userId") String userId,
                             @Param("sessionId") String sessionId,
                             @Param("question") String question,
                             @Param("answer") String answer,
                             @Param("embedding") String embedding);

    @Insert("INSERT INTO chat_messages (user_id, session_id, question, answer, created_at) " +
            "VALUES (#{userId}, #{sessionId}, #{question}, #{answer}, NOW())")
    int insert(ChatMessage msg);

    @Select("SELECT id, user_id, session_id, question, answer, created_at " +
            "FROM chat_messages WHERE session_id = #{sessionId} ORDER BY created_at")
    List<ChatMessage> findBySessionId(@Param("sessionId") String sessionId);

    @Select("SELECT id, user_id, session_id, question, answer, created_at, " +
            "1 - (embedding <=> #{embedding}::vector) AS similarity " +
            "FROM chat_messages WHERE user_id = #{userId} " +
            "ORDER BY embedding <=> #{embedding}::vector LIMIT #{topK}")
    List<ChatMessage> findSimilarByEmbedding(@Param("userId") String userId,
                                              @Param("embedding") String embedding,
                                              @Param("topK") int topK);

    @Select("SELECT id, user_id, session_id, question, answer, created_at " +
            "FROM chat_messages WHERE user_id = #{userId} " +
            "AND (question ILIKE '%' || #{keyword} || '%' OR answer ILIKE '%' || #{keyword} || '%') " +
            "ORDER BY created_at DESC LIMIT #{topK}")
    List<ChatMessage> findByKeyword(@Param("userId") String userId,
                                    @Param("keyword") String keyword,
                                    @Param("topK") int topK);

    @Select("SELECT session_id AS sessionId, " +
            "SUBSTRING(MIN(question), 1, 30) AS title, " +
            "MIN(created_at) AS createdAt, " +
            "COUNT(*) AS messageCount " +
            "FROM chat_messages WHERE user_id = #{userId} " +
            "GROUP BY session_id ORDER BY MIN(created_at) DESC")
    List<SessionSummary> findSessionsByUserId(@Param("userId") String userId);

    @Select("SELECT id, user_id, session_id, question, answer, created_at " +
            "FROM chat_messages WHERE user_id = #{userId} " +
            "ORDER BY created_at DESC LIMIT #{limit}")
    List<ChatMessage> findRecentByUser(@Param("userId") String userId,
                                        @Param("limit") int limit);

    @Delete("DELETE FROM chat_messages WHERE session_id = #{sessionId}")
    int deleteBySessionId(@Param("sessionId") String sessionId);
}
