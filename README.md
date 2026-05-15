---

# ☁️ Cloud Locker & Mega File Transfer Suite

Welcome to the **Cloud Locker & File Transfer Suite** repository. This project demonstrates the evolution of a custom cloud storage and file-sharing architecture across three distinct versions.

What started as a secure, personal file locker has evolved into a multi-user room environment, and finally, an experimental high-speed file transfer protocol.

## 📂 Repository Structure

This repository contains three independent project directories, each representing a different phase of development and a unique approach to handling file streams and memory:

1. `my_cloud_locker_v1`
2. `my_cloud_locker_multiuser_v2`
3. `MEGA FILE TRANSFER 3 PROJECTS_v3.1`

---

## 🚀 Version Breakdown & Highlights

### 🛡️ Version 1: `my_cloud_locker_v1` (The Foundation)

**Focus:** Security and Basic Reliability
**Architecture:** Chunk-based processing

This is the foundational version of the project. It was designed as a secure, single-user locker for personal files.

* **Authentication:** Implements robust user authentication to ensure files are kept private and secure.
* **Memory Management (Chunking):** To prevent server crashes when handling larger files, this version uses a **chunking concept**. Files are broken down into smaller, manageable pieces (chunks) during upload and download. This ensures a low and stable memory footprint, making it highly reliable on machines with limited RAM.

### 👥 Version 2: `my_cloud_locker_multiuser_v2` (The Collaboration Update)

**Focus:** Multi-user Sharing & Session Management
**Architecture:** Chunk-based processing with Room logic

Building upon the stability of v1, this version introduces collaborative features by implementing a "Room" concept.

* **Room-Based Sharing:** Users can join specific, isolated rooms to share files with a select group of people, making it ideal for team collaborations or project sharing.
* **Continued Efficiency:** Like v1, this version retains the **chunking architecture**. It scales well for multiple users simultaneously uploading and downloading files without overwhelming the server's memory capacity.

### ⚡ Version 3: `MEGA FILE TRANSFER 3 PROJECTS_v3.1` (The Speed Demon)

**Focus:** Maximum Transfer Speed for Large Files
**Architecture:** RAM-Intensive Full-Block Allocation (No Chunking)

This version is an experimental pivot focusing entirely on raw transfer speed, purposefully trading memory efficiency for maximum I/O performance.

* **High-Speed Transfer:** Designed specifically for rapid, large-scale file transfers across networks.
* **RAM-Intensive Architecture:** **This version abandons the chunking concept.** Instead, it allocates a block of memory in the system's RAM equal to the entire size of the file being transferred.
* **The Trade-off:** By reading and writing the entire file into RAM at once, disk I/O bottlenecks are minimized, resulting in blistering transfer speeds. However, this comes at a significant cost: **it is highly RAM-consuming**. Attempting to transfer a file larger than your available server RAM will result in memory exhaustion. Use with caution in production environments!

---





## ⚠️ Important Note on v3.1 Usage

When testing `MEGA FILE TRANSFER 3 PROJECTS_v3.1`, monitor your system's resources closely. Due to its architecture, transferring a 4GB file will require an immediate allocation of 4GB of RAM.

---

*This suite was built to explore the trade-offs between memory-safe stream processing and raw memory-mapped speed.*
