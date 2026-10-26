-- ==========================================================
-- BloodConnect: MySQL Database Dump for Viva / Project Submission
-- Target: MySQL 5.7+ / MySQL 8.0 / MariaDB
-- ==========================================================

CREATE DATABASE IF NOT EXISTS `bloodconnect` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `bloodconnect`;

DROP TABLE IF EXISTS `notifications`;
DROP TABLE IF EXISTS `blood_requests`;
DROP TABLE IF EXISTS `donors`;
DROP TABLE IF EXISTS `users`;

-- 1. Users Table
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(120) NOT NULL,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `phone` VARCHAR(30) NOT NULL,
    `role` ENUM('donor', 'requester', 'admin') NOT NULL DEFAULT 'donor',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Donors Table
CREATE TABLE `donors` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `blood_group` ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    `city` VARCHAR(80) NOT NULL,
    `address` TEXT,
    `latitude` DECIMAL(10, 7) DEFAULT 13.0827,
    `longitude` DECIMAL(10, 7) DEFAULT 80.2707,
    `is_available` TINYINT(1) DEFAULT 1,
    `is_verified` TINYINT(1) DEFAULT 0,
    `last_donation_date` DATE NULL,
    `total_donations` INT DEFAULT 0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_donors_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Blood Requests Table
CREATE TABLE `blood_requests` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `requester_id` INT NOT NULL,
    `patient_name` VARCHAR(120) NOT NULL,
    `blood_group` ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    `units_needed` INT DEFAULT 1,
    `hospital` VARCHAR(150) NOT NULL,
    `city` VARCHAR(80) NOT NULL,
    `contact_phone` VARCHAR(30) NOT NULL,
    `urgency` ENUM('Normal', 'Urgent', 'Critical') DEFAULT 'Urgent',
    `status` ENUM('Open', 'Fulfilled', 'Closed') DEFAULT 'Open',
    `notes` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_requests_user` FOREIGN KEY (`requester_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Notifications Table
CREATE TABLE `notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `title` VARCHAR(150) NOT NULL,
    `message` TEXT NOT NULL,
    `type` ENUM('emergency', 'verification', 'info') DEFAULT 'info',
    `is_read` TINYINT(1) DEFAULT 0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_notifications_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Search indices
CREATE INDEX `idx_donors_search` ON `donors`(`blood_group`, `city`, `is_available`, `is_verified`);
CREATE INDEX `idx_requests_status` ON `blood_requests`(`status`, `urgency`, `blood_group`);

-- Blood-bank inventory, separate from volunteer donors.
CREATE TABLE IF NOT EXISTS `blood_banks` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(160) NOT NULL,
    `email` VARCHAR(160) NOT NULL UNIQUE,
    `phone` VARCHAR(40) NOT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `license_number` VARCHAR(100) NOT NULL,
    `city` VARCHAR(100) NOT NULL,
    `address` TEXT NOT NULL,
    `latitude` DECIMAL(10, 7) DEFAULT 13.0827,
    `longitude` DECIMAL(10, 7) DEFAULT 80.2707,
    `is_verified` TINYINT(1) NOT NULL DEFAULT 0,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `blood_bank_stock` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `blood_bank_id` INT NOT NULL,
    `blood_group` VARCHAR(5) NOT NULL,
    `component` VARCHAR(40) NOT NULL,
    `units_available` INT NOT NULL DEFAULT 0,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uq_bank_stock` (`blood_bank_id`, `blood_group`, `component`),
    CONSTRAINT `chk_bank_stock_units` CHECK (`units_available` >= 0),
    CONSTRAINT `fk_stock_bank` FOREIGN KEY (`blood_bank_id`) REFERENCES `blood_banks`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
