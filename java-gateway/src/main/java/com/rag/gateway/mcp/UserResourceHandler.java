package com.rag.gateway.mcp;

import com.rag.gateway.dto.ApiResponse;
import com.rag.gateway.model.User;
import com.rag.gateway.repository.mysql.UserMapper;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;

@Component
public class UserResourceHandler {

    private final UserMapper userMapper;

    public UserResourceHandler(UserMapper userMapper) {
        this.userMapper = userMapper;
    }

    public ApiResponse<?> getProfile(String userId) {
        try {
            User user = userMapper.findById(Long.parseLong(userId));
            if (user == null) {
                return ApiResponse.error(404, "user not found");
            }
            Map<String, Object> profile = new LinkedHashMap<>();
            profile.put("name", user.getUsername());
            profile.put("preferences", user.getPreferences());
            profile.put("plan", user.getPlan());
            return ApiResponse.success(profile);
        } catch (NumberFormatException e) {
            return ApiResponse.error(400, "invalid user id");
        }
    }

    public ApiResponse<?> getPermissions(String userId) {
        Map<String, Object> perms = new LinkedHashMap<>();
        perms.put("roles", new String[]{"user"});
        perms.put("scopes", new String[]{"chat:read", "chat:write"});
        return ApiResponse.success(perms);
    }
}