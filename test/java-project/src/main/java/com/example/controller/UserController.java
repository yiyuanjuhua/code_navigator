package com.example.controller;

import com.example.service.UserService;
import com.example.dto.UserResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
public class UserController {

    @Autowired
    private UserService userService;

    @GetMapping("/{id}")
    public UserResponse getUserById(@PathVariable Long id) {
        return userService.findUserById(id);
    }

    @PostMapping
    public UserResponse createUser(@RequestBody String username) {
        return userService.createNewUser(username);
    }

    @DeleteMapping("/{id}")
    public void deleteUser(@PathVariable Long id) {
        userService.deleteUserById(id);
    }
}