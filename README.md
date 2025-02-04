## Inspiration
We got our inspiration from the Indian Premier League (IPL) a Cricket Game, which is renowned for its exciting and interactive fan experiences. The IPL has done an amazing job of using technology to bring fans closer to the game with real-time statistics, engaging commentary, and interactive features. By applying these principles to Major League Baseball (MLB), we believe we can transform how baseball fans enjoy the game.
 
Lessons from the IPL:
Real-Time Engagement:
The IPL keeps fans hooked with live score updates, instant replays, and interactive polls. We aim to bring these elements to baseball to make the viewing experience more dynamic.
 
Multi-Platform Accessibility:
The IPL can be accessed via mobile apps, websites, and social media. We want our application to be available on multiple platforms to reach a wider audience.
 
Enhanced Commentary and Analysis:
IPL broadcasts feature expert commentary that helps fans understand the game better. By using video analysis and AI, we can offer real-time insights and explanations for baseball.
 
Fan Interaction:
The IPL encourages fan interaction through social media and live chats. We plan to include an AI-powered chat interface to create a more interactive experience for baseball fans.
 
Video Language Model:
Integrating a video language model into our project will allow us to analyze live game footage in real time, offering insightful commentary and interactive tooltips. This technology will help us explain strategies, provide player statistics, and answer fan queries instantly.
 
**Applying IPL Principles to MLB:**
By drawing from the IPL and using advanced video language models, we aim to:
Enhance viewer engagement with real-time video analysis.
Make the game accessible with AI-powered commentary.
Encourage fan interaction through live chats on video of current game.
 
## What it does
Our project consists of two main components: a frontend interface where users can watch live baseball video streams and interact through a chat interface, and a backend system that powers the intelligent features. The frontend provides fans with real-time information about the matches and important events. It includes an Agentic chat feature that analyzes the live video stream and allows fans to interact with the current happenings or inquire about historical events in the match. Fans can ask questions about strategies, get explanations of the current plays, and receive relevant information in a textual format. This creates a more engaging and informative experience for baseball fans, helping them stay connected and informed throughout the game.
 
## How we built it
Our architecture focuses on both the user interface (UI) and the backend. We used the Agentic Framework to manage real-time interactions and implemented the Gemini multimodal Vision model for video analysis. Vertex AI was employed for retrieval-augmented generation (RAG) to provide historical information. For video extraction and segmentation, we used MoviePy, which allowed us to split the video into 30-second intervals for detailed analysis. The frontend was built using React, ensuring a responsive and interactive user experience. The backend processes the video content and manages the AI-driven interactions, creating a seamless integration between the live video stream and the chat interface.
 
## Challenges we ran into
We encountered several challenges during development. Managing live streaming required handling network-related issues and downloading and segmenting the video efficiently. Ensuring fast interaction speed and video processing was critical, but Google Cloud credits limited our ability to perform extensive performance testing. Transitioning from Azure to Google Cloud involved a steep learning curve, which took additional time to overcome. Hosting the application also posed challenges due to credit limitations on Google Cloud, which delayed some aspects of our deployment. Despite these hurdles, we successfully integrated the necessary technologies to achieve our goals.
 
## Accomplishments that we're proud of
- Real-Time Highlights: We achieved the ability to generate real-time highlights during the match, complete with video explanations of each clip.
- Agentic Framework Integration: Fans can interact in real-time, and if they miss the first few minutes of the match, they can receive a summary to catch up quickly.
- Historical Analysis: Our system can extract and analyze historical events in real-time, providing a comprehensive view of the match.
- Strategy Interaction: Fans can inquire about current strategies and counter-strategies being employed in the game.
- Live API Integration: We successfully integrated major events from the live API, ensuring up-to-date information.
 
##What we learned
--Video to Text and Vision Model Usage: We gained valuable experience in converting video content to text and utilizing vision models for real-time analysis.
--Gemini-2.0 Model: We found the experimental Gemini-2.0 multimodal model to be effective and superior to other vision models like LLAMA currently available in the market.
--Google Cloud Integration: We learned to integrate frontend and backend services on Google Cloud, improving our overall cloud deployment skills.
 
##What's next for Curveball Nexus BLR
--Internal Implementation: We plan to apply a similar approach for vision-based use cases within our company, leveraging the techniques and technologies we've developed.
--Plug-and-Play Solution: We aim to refine our Agentic framework to create a plug-and-play solution for baseball fan engagement on MLB platforms. This will make it easier to deploy our interactive and intelligent features across different baseball fan applications, enhancing the overall fan experience.

## Architecture
![image](https://github.com/user-attachments/assets/cee78679-03cd-420d-a091-c473856a2867)

## Setup and Run Guide

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Backend Setup
```bash
cd backend_python
pip install -r requirements.txt
python backend_Server.py
```

## Meet Team CurveBall Nexus BLR
| Dr. Prashant Ramappa | Gagan Yadav S | Druva Hegde | Himanshu Nanda |
|:---:|:---:|:---:|:---:|
| <img src="https://github.com/user-attachments/assets/883a1f01-8dba-4046-bf9c-412c8fcc3d57" style="width:250px;height:250px;object-fit:cover;object-position:center;"> | <img src="https://github.com/user-attachments/assets/e726e7aa-5da8-4934-965c-71d457957229" style="width:250px;height:250px;object-fit:cover;object-position:center;"> | <img src="https://github.com/user-attachments/assets/7143b896-35b8-4eb8-a945-4cf4a7214549" style="width:250px;height:250px;object-fit:cover;object-position:center;"> | <img src="https://github.com/user-attachments/assets/7ac098d8-518d-49e9-b291-b70fa74c5fba" style="width:250px;height:250px;object-fit:cover;object-position:center;"> |


## Snapshots

| Loading Page |
|:---:|
| ![image](https://github.com/user-attachments/assets/b320204d-3097-4873-a693-69691d33c860) |

| Flip it once |
|:---:|
| ![image](https://github.com/user-attachments/assets/3c3931eb-c9f1-471d-81fb-a98a5815c091) |

| Nexus AI Chat Assistant |
|:---:|
| ![image](https://github.com/user-attachments/assets/ce09500b-625a-4874-a60b-95631cbd40ec) |

| Result |
|:---:|
| ![image](https://github.com/user-attachments/assets/4e469be8-7939-4567-aed0-9dce118fb0bd) |

| Result |
|:---:|
| ![image](https://github.com/user-attachments/assets/f8c6ddb2-922f-4627-a9db-9356c9131090) |








