package com.example.service;

import com.example.dto.UserResponse;
import com.example.repository.UserRepository;
import com.example.util.ValidationUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class UserService {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private ValidationUtil validationUtil;

    public UserResponse findUserById(Long id) {
        validationUtil.validateId(id);
        return userRepository.getUserById(id);
    }

    public UserResponse createNewUser(String username) {
        validationUtil.validateUsername(username);
        UserResponse user = buildUserResponse(username);
        return userRepository.saveUser(user);
    }

    public void deleteUserById(Long id) {
        validationUtil.validateId(id);
        userRepository.deleteUser(id);
    }

    private UserResponse buildUserResponse(String username) {
        UserResponse response = new UserResponse();
        response.setUsername(username);
        response.setId(generateUserId());
        return response;
    }

    private Long generateUserId() {
        return System.currentTimeMillis();
    }
}