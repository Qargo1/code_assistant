import random

class CSharpExerciseGenerator:
    TOPICS = {
        "basics": [
            {
                "question": "Напишите программу для вычисления факториала числа",
                "template": "public class Factorial {{\n  public static int Calculate(int n) {{\n    // Ваш код здесь\n  }}\n}}",
                "tests": [
                    {"input": 5, "output": 120},
                    {"input": 0, "output": 1}
                ]
            }
        ],
        "oop": [
            {
                "question": "Создайте класс 'Car' с полями Brand и Year",
                "template": "public class Car {{\n  // Добавьте поля\n\n  // Добавьте конструктор\n}}",
                "tests": [...] 
            }
        ]
    }

    def generate_exercise(self, topic: str) -> dict:
        return random.choice(self.TOPICS[topic])