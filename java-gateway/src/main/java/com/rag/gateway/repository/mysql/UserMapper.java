package com.rag.gateway.repository.mysql;

import com.rag.gateway.model.User;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface UserMapper {

    @Select("SELECT id, username, password_hash, plan, preferences, created_at FROM users WHERE id = #{id}")
    User findById(@Param("id") Long id);

    @Select("SELECT id, username, password_hash, plan, preferences, created_at FROM users WHERE username = #{username}")
    User findByUsername(@Param("username") String username);
}
