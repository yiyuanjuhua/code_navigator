package com.example.repository;

import com.example.dto.UserResponse;
import org.springframework.stereotype.Repository;
import java.util.HashMap;
import java.util.Map;

@Repository
public class UserRepository {

    private Map<Long, UserResponse> userDatabase = new HashMap<>();

    public UserResponse getUserById(Long id) {
        return userDatabase.get(id);
    }

    public UserResponse saveUser(UserResponse user) {
        userDatabase.put(user.getId(), user);
        return user;
    }

    public void deleteUser(Long id) {
        userDatabase.remove(id);
    }

    public boolean existsById(Long id) {
        return userDatabase.containsKey(id);
    }
}