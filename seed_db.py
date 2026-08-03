import datetime
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import your existing models from your script
# (Assuming your file is named models.py; adjust import if needed)
from database import Base, User, Conversation, Message, SurveyResponse, Clinic, engine, SessionLocal


def seed_database():
    session = SessionLocal()

    try:
        print("Seeding database with initial test data...")

        # ---------------------------------------------------------
        # 1. SEED USERS (10 Users)
        # ---------------------------------------------------------
        users_data = [
            User(username="aaria_k", email="aaria@example.com", password_hash="hash_aaria_123"),
            User(username="bilal_m", email="bilal@example.com", password_hash="hash_bilal_456"),
            User(username="cyber_sam", email="sam@example.com", password_hash="hash_sam_789"),
            User(username="daniyal_a", email="daniyal@example.com", password_hash="hash_daniyal_321"),
            User(username="eisha_r", email="eisha@example.com", password_hash="hash_eisha_654"),
            User(username="fatima_z", email="fatima@example.com", password_hash="hash_fatima_987"),
            User(username="hassan_v", email="hassan@example.com", password_hash="hash_hassan_111"),
            User(username="iqra_t", email="iqra@example.com", password_hash="hash_iqra_222"),
            User(username="jamal_k", email="jamal@example.com", password_hash="hash_jamal_333"),
            User(username="khadija_n", email="khadija@example.com", password_hash="hash_khadija_444"),
        ]

        session.add_all(users_data)
        session.flush()  # Flushes to generate auto-increment primary keys (user.id)
        print(f"Added {len(users_data)} users.")

        # ---------------------------------------------------------
        # 2. SEED CONVERSATIONS (12 Conversations)
        # ---------------------------------------------------------
        conversations_data = [
            Conversation(user_id=users_data[0].id, title="Late Night Anxiety & Overthinking"),
            Conversation(user_id=users_data[0].id, title="Weekly Mental Health Check-in"),
            Conversation(user_id=users_data[1].id, title="Workplace Burnout Reflection"),
            Conversation(user_id=users_data[2].id, title="Exam Stress Management"),
            Conversation(user_id=users_data[3].id, title="Social Isolation Thoughts"),
            Conversation(user_id=users_data[4].id, title="Grief and Loss Support"),
            Conversation(user_id=users_data[5].id, title="Panic Attack Recovery"),
            Conversation(user_id=users_data[6].id, title="Daily Gratitude Journal"),
            Conversation(user_id=users_data[7].id, title="Imposter Syndrome Talk"),
            Conversation(user_id=users_data[8].id, title="Sleep Deprivation Concerns"),
            Conversation(user_id=users_data[9].id, title="Managing Sudden Anger"),
            Conversation(user_id=users_data[9].id, title="Relationship Conflict Debrief"),
        ]

        session.add_all(conversations_data)
        session.flush()
        print(f"Added {len(conversations_data)} conversations.")

        # ---------------------------------------------------------
        # 3. SEED MESSAGES (15 Messages)
        # ---------------------------------------------------------
        messages_data = [
            # Conversation 1 (Aaria)
            Message(
                conversation_id=conversations_data[0].id,
                sender="user",
                message_text="I can't sleep. My chest feels really tight and I feel extremely overwhelmed about tomorrow.",
                sentiment_score=0.82  # Fear/Anxiety
            ),
            Message(
                conversation_id=conversations_data[0].id,
                sender="assistant",
                message_text="I hear you, and it's okay. Let's take a slow breath together. Would you like to try a grounding exercise?",
                sentiment_score=0.05
            ),
            Message(
                conversation_id=conversations_data[0].id,
                sender="user",
                message_text="Yes please, I feel so lost right now.",
                sentiment_score=0.74
            ),

            # Conversation 2 (Bilal)
            Message(
                conversation_id=conversations_data[2].id,
                sender="user",
                message_text="I gave up on my presentation today. My boss was shouting and I felt completely incompetent.",
                sentiment_score=0.89  # Sadness / Anger
            ),
            Message(
                conversation_id=conversations_data[2].id,
                sender="assistant",
                message_text="That sounds exhausting and painful. It makes complete sense why you'd feel disheartened.",
                sentiment_score=0.10
            ),

            # Conversation 3 (Sam)
            Message(
                conversation_id=conversations_data[3].id,
                sender="user",
                message_text="Finals are in two days and I haven't finished half the syllabus!",
                sentiment_score=0.91
            ),
            Message(
                conversation_id=conversations_data[3].id,
                sender="assistant",
                message_text="Let's break down your study topics into 30-minute blocks to regain control.",
                sentiment_score=0.02
            ),

            # Conversation 4 (Daniyal)
            Message(
                conversation_id=conversations_data[4].id,
                sender="user",
                message_text="I haven't left my room in three days. Nobody has texted me either.",
                sentiment_score=0.85
            ),

            # Conversation 5 (Eisha)
            Message(
                conversation_id=conversations_data[5].id,
                sender="user",
                message_text="I miss my grandmother so much today. Everything reminds me of her.",
                sentiment_score=0.78
            ),

            # Conversation 6 (Fatima)
            Message(
                conversation_id=conversations_data[6].id,
                sender="user",
                message_text="I had a sudden panic attack at the grocery store.",
                sentiment_score=0.95
            ),

            # Conversation 7 (Hassan)
            Message(
                conversation_id=conversations_data[7].id,
                sender="user",
                message_text="I had a really productive morning walk today and felt quite cheerful!",
                sentiment_score=0.01  # Positive / Low Distress
            ),

            # Conversation 8 (Iqra)
            Message(
                conversation_id=conversations_data[8].id,
                sender="user",
                message_text="Everyone at my new job is so smart. I feel like a complete fraud.",
                sentiment_score=0.79
            ),

            # Conversation 9 (Jamal)
            Message(
                conversation_id=conversations_data[9].id,
                sender="user",
                message_text="I haven't slept more than 3 hours a night this entire week.",
                sentiment_score=0.68
            ),

            # Conversation 10 (Khadija)
            Message(
                conversation_id=conversations_data[10].id,
                sender="user",
                message_text="I lost my temper during the team meeting and slammed my desk.",
                sentiment_score=0.88  # Anger
            ),
            Message(
                conversation_id=conversations_data[10].id,
                sender="assistant",
                message_text="It's understandable to feel frustrated. Let's explore what triggered that spike before deciding how to handle it.",
                sentiment_score=0.04
            )
        ]

        session.add_all(messages_data)
        print(f"Added {len(messages_data)} messages.")

        # ---------------------------------------------------------
        # 4. SEED SURVEY RESPONSES (10 Responses with JSONB Data)
        # ---------------------------------------------------------
        survey_responses_data = [
            SurveyResponse(
                user_id=users_data[0].id,
                survey_data={
                    "gad7_score": 14,
                    "phq9_score": 11,
                    "primary_concern": "Anxiety & Insomnia",
                    "emotions_vector": {"sadness": 0.2, "joy": 0.05, "love": 0.0, "anger": 0.1, "fear": 0.6,
                                        "surprise": 0.05}
                }
            ),
            SurveyResponse(
                user_id=users_data[1].id,
                survey_data={
                    "gad7_score": 8,
                    "phq9_score": 16,
                    "primary_concern": "Depression / Burnout",
                    "emotions_vector": {"sadness": 0.7, "joy": 0.0, "love": 0.05, "anger": 0.15, "fear": 0.1,
                                        "surprise": 0.0}
                }
            ),
            SurveyResponse(
                user_id=users_data[2].id,
                survey_data={
                    "gad7_score": 18,
                    "phq9_score": 9,
                    "primary_concern": "Academic Panic",
                    "emotions_vector": {"sadness": 0.1, "joy": 0.0, "love": 0.0, "anger": 0.2, "fear": 0.7,
                                        "surprise": 0.0}
                }
            ),
            SurveyResponse(
                user_id=users_data[3].id,
                survey_data={
                    "gad7_score": 6,
                    "phq9_score": 14,
                    "primary_concern": "Social Withdrawal",
                    "emotions_vector": {"sadness": 0.65, "joy": 0.0, "love": 0.0, "anger": 0.05, "fear": 0.3,
                                        "surprise": 0.0}
                }
            ),
            SurveyResponse(
                user_id=users_data[4].id,
                survey_data={
                    "gad7_score": 10,
                    "phq9_score": 18,
                    "primary_concern": "Grief",
                    "emotions_vector": {"sadness": 0.8, "joy": 0.0, "love": 0.1, "anger": 0.05, "fear": 0.05,
                                        "surprise": 0.0}
                }
            ),
            SurveyResponse(
                user_id=users_data[5].id,
                survey_data={
                    "gad7_score": 19,
                    "phq9_score": 12,
                    "primary_concern": "Panic Disorder",
                    "emotions_vector": {"sadness": 0.1, "joy": 0.0, "love": 0.0, "anger": 0.0, "fear": 0.85,
                                        "surprise": 0.05}
                }
            ),
            SurveyResponse(
                user_id=users_data[6].id,
                survey_data={
                    "gad7_score": 3,
                    "phq9_score": 2,
                    "primary_concern": "General Wellbeing",
                    "emotions_vector": {"sadness": 0.05, "joy": 0.7, "love": 0.2, "anger": 0.0, "fear": 0.05,
                                        "surprise": 0.0}
                }
            ),
            SurveyResponse(
                user_id=users_data[7].id,
                survey_data={
                    "gad7_score": 11,
                    "phq9_score": 7,
                    "primary_concern": "Imposter Syndrome",
                    "emotions_vector": {"sadness": 0.3, "joy": 0.0, "love": 0.0, "anger": 0.1, "fear": 0.6,
                                        "surprise": 0.0}
                }
            ),
            SurveyResponse(
                user_id=users_data[8].id,
                survey_data={
                    "gad7_score": 12,
                    "phq9_score": 10,
                    "primary_concern": "Chronic Sleep Loss",
                    "emotions_vector": {"sadness": 0.4, "joy": 0.0, "love": 0.0, "anger": 0.2, "fear": 0.4,
                                        "surprise": 0.0}
                }
            ),
            SurveyResponse(
                user_id=users_data[9].id,
                survey_data={
                    "gad7_score": 9,
                    "phq9_score": 8,
                    "primary_concern": "Emotional Dysregulation / Anger",
                    "emotions_vector": {"sadness": 0.1, "joy": 0.0, "love": 0.0, "anger": 0.75, "fear": 0.1,
                                        "surprise": 0.05}
                }
            )
        ]

        session.add_all(survey_responses_data)
        print(f"Added {len(survey_responses_data)} survey responses.")

        # ---------------------------------------------------------
        # 5. SEED CLINICS (12 Physical Clinic / Hospital Locations)
        # ---------------------------------------------------------
        clinics_data = [
            Clinic(
                name="Islamabad Psychiatric & Counseling Center",
                address="Sector F-7/2, Street 14, Islamabad",
                phone="+92-51-2651122",
                latitude=33.7215,
                longitude=73.0562
            ),
            Clinic(
                name="Shifa International Hospital - Psychiatry Dept",
                address="Pitras Bukhari Road, H-8/4, Islamabad",
                phone="+92-51-8463000",
                latitude=33.6844,
                longitude=73.0792
            ),
            Clinic(
                name="Ali Medical Centre - Behavioral Sciences",
                address="Kohistan Road, F-8/3, Islamabad",
                phone="+92-51-8090200",
                latitude=33.7121,
                longitude=73.0381
            ),
            Clinic(
                name="Mind Care Clinic Rawalpindi",
                address="Peshawar Road, Westridge 1, Rawalpindi",
                phone="+92-51-5182345",
                latitude=33.5971,
                longitude=73.0289
            ),
            Clinic(
                name="Maroof International Hospital - Wellness Center",
                address="10th Avenue, F-10/3, Islamabad",
                phone="+92-51-2222920",
                latitude=33.6983,
                longitude=73.0031
            ),
            Clinic(
                name="Combined Military Hospital (CMH) - Psychiatry Unit",
                address="Mall Road, Saddar, Rawalpindi",
                phone="+92-51-5568820",
                latitude=33.5932,
                longitude=73.0543
            ),
            Clinic(
                name="PIMS Hospital - Department of Psychiatry",
                address="Ibn-e-Sina Road, G-8/3, Islamabad",
                phone="+92-51-9261170",
                latitude=33.7022,
                longitude=73.0558
            ),
            Clinic(
                name="Kulsum International Hospital - Psychology Department",
                address="Blue Area, Sector G-6/2, Islamabad",
                phone="+92-51-8449100",
                latitude=33.7180,
                longitude=73.0675
            ),
            Clinic(
                name="Quaid-e-Azam International Hospital",
                address="Near Golra Mode, Peshawar Road, Islamabad",
                phone="+92-51-8449100",
                latitude=33.6369,
                longitude=72.9691
            ),
            Clinic(
                name="Clear Vision Mental Health Clinic",
                address="Civic Center, Phase 4 Bahria Town, Rawalpindi",
                phone="+92-51-5730111",
                latitude=33.5244,
                longitude=73.1022
            ),
            Clinic(
                name="Maxhealth Hospital & Mind Wellness",
                address="21-K, Markaz G-8, Islamabad",
                phone="+92-51-2255012",
                latitude=33.7045,
                longitude=73.0489
            ),
            Clinic(
                name="NUST Student Counseling & Therapy Office",
                address="NUST Main Campus, H-12, Islamabad",
                phone="+92-51-90851500",
                latitude=33.6425,
                longitude=72.9930
            )
        ]

        session.add_all(clinics_data)
        print(f"Added {len(clinics_data)} physical clinics.")

        # Commit everything to the database
        session.commit()
        print("\nALL TEST DATA SUCCESSFULLY COMMITTED TO POSTGRESQL!")

    except Exception as e:
        session.rollback()
        print(f" Error inserting dummy data: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()