package com.example.util;

import org.springframework.stereotype.Component;

@Component
public class ValidationUtil {

    public void validateId(Long id) {
        if (id == null || id <= 0) {
            throw new IllegalArgumentException("Invalid ID: " + id);
        }
    }

    public void validateUsername(String username) {
        if (username == null || username.trim().isEmpty()) {
            throw new IllegalArgumentException("Username cannot be empty");
        }
        if (username.length() < 2) {
            throw new IllegalArgumentException("Username too short");
        }
    }

    private boolean isValidFormat(String input) {
        return input != null && input.matches("^[a-zA-Z0-9_]+$");
    }
}