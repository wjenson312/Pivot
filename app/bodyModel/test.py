import cv2
import numpy as np
import mediapipe as mp


def main():
    """Main function for pose detection and tracking"""
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(static_image_mode=False,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5)

    cap = cv2.VideoCapture('your_video.mp4')  # or 0 for webcam

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Convert BGR to RGB
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process the frame
        results = pose.process(image)

        if results.pose_world_landmarks:
            # We now have 3D world coordinates (x, y, z) in meters (approx)
            landmarks = results.pose_world_landmarks.landmark
            # Example: get hip (left) vs knee (left)
            hip_l = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
            knee_l = landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value]
            ankle_l = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value]

            print("Left hip 3D:", (hip_l.x, hip_l.y, hip_l.z))
            print("Left knee 3D:", (knee_l.x, knee_l.y, knee_l.z))
            print("Left ankle 3D:", (ankle_l.x, ankle_l.y, ankle_l.z))

        # (Optional) Show the frame with landmarks drawn
        annotated = frame.copy()
        mp.solutions.drawing_utils.draw_landmarks(
            annotated, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        cv2.imshow('Frame', annotated)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()