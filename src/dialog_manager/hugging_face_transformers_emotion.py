import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class EmotionAnalyzer:
    def __init__(self):
        # 모델 및 토크나이저 로드
        self.MODEL_NAME = "hun3359/klue-bert-base-sentiment"
        self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.MODEL_NAME)

        # 모델 설정에서 id2label 맵핑 로드
        self.id2label = self.model.config.id2label
        """
        "id2label":{
            "0": "분노",
            "1": "툴툴대는",
            "2": "좌절한",
            "3": "짜증내는",
            "4": "방어적인",
            "5": "악의적인",
            "6": "안달하는",
            "7": "구역질 나는",
            "8": "노여워하는",
            "9": "성가신",
            "10": "슬픔",
            "11": "실망한",
            "12": "비통한",
            "13": "후회되는",
            "14": "우울한",
            "15": "마비된",
            "16": "염세적인",
            "17": "눈물이 나는",
            "18": "낙담한",
            "19": "환멸을 느끼는",
            "20": "불안",
            "21": "두려운",
            "22": "스트레스 받는",
            "23": "취약한",
            "24": "혼란스러운",
            "25": "당혹스러운",
            "26": "회의적인",
            "27": "걱정스러운",
            "28": "조심스러운",
            "29": "초조한",
            "30": "상처",
            "31": "질투하는",
            "32": "배신당한",
            "33": "고립된",
            "34": "충격 받은",
            "35": "가난한 불우한",
            "36": "희생된",
            "37": "억울한",
            "38": "괴로워하는",
            "39": "버려진",
            "40": "당황",
            "41": "고립된(당황한)",
            "42": "남의 시선을 의식하는",
            "43": "외로운",
            "44": "열등감",
            "45": "죄책감의",
            "46": "부끄러운",
            "47": "혐오스러운",
            "48": "한심한",
            "49": "혼란스러운(당황한)",
            "50": "기쁨",
            "51": "감사하는",
            "52": "신뢰하는",
            "53": "편안한",
            "54": "만족스러운",
            "55": "흥분",
            "56": "느긋",
            "57": "안도",
            "58": "신이 난",
            "59": "자신하는"
        },
        """

        # 원하는 감정 번호만 포함하는 감정 그룹 매핑
        self.emotion_map = {
            "기쁨": [50, 51, 52, 54, 58],
            "짜증난": [1, 3, 6, 7, 9],
            "슬픔": [2, 10, 11, 12, 13, 14, 17, 18, 36, 37, 38, 40, 41, 43, 44, 45, ],
            "부정": [15, 16, 19, 20, 21, 22, 23, 24, 25, 26, 27, 30, 31, 32, 33, 48, 49, 55],
            "화남": [0, 5, 8, 16, 47],
            "중립": [4, 28, 29, 34, 35, 39, 42, 46, 53, 56, 57, 59]
        }

    def analyze_emotion(self, text):
        
        print(f"입력된 문장: {text}")
        # 입력 문장 토큰화
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)

        # 모델 예측 수행 (No Grad 모드에서 실행)
        with torch.no_grad():
            outputs = self.model(**inputs)

        # 가장 높은 확률을 가진 감정 레이블 예측
        predicted_label_id = torch.argmax(outputs.logits, dim=1).item()
        
        detected_emotion = "중립"
        for emotion_temp, ids in self.emotion_map.items():
            if predicted_label_id in ids:
                detected_emotion = emotion_temp
                break  # 첫 번째 일치하는 감정만 적용

        print(f"Raw prediction: {predicted_label_id} -> {detected_emotion}")  # 디버깅용 출력

        return detected_emotion

def main():
    print("터미널 감정 분석기 시작 (종료하려면 '종료' 입력):")
    analyzer = EmotionAnalyzer()

    while True:
        user_input = input("분석할 문장을 입력하세요: ").strip()
        if user_input.lower() == "종료":
            print("프로그램을 종료합니다.")
            break

        result = analyzer.analyze_emotion(user_input)
        # print(f"입력된 문장: {user_input}")
        print(f"감정: {result}")

if __name__ == "__main__":
    main()