# F:\AI-M2\managers\ocr\ocr_utils.py
import re
import logging
from typing import List, Dict, Optional

class OCRHelper:
    """OCR 후처리 및 데이터 검증 헬퍼 클래스."""

    @staticmethod
    def validate_extracted_text(text: str) -> bool:
        """추출된 텍스트의 유효성 검사."""
        return bool(text.strip())

    @staticmethod
    def extract_cell_and_kclb(text: str) -> Dict[str, Optional[str]]:
        """KCLB 번호 및 Cell 이름 추출."""
        try:
            kclb_pattern = r"KCLB\s*Number\s*:\s*(\d+)"
            cell_name_pattern = r"Cell\s*Name\s*:\s*([^\n]+)"

            kclb_match = re.search(kclb_pattern, text, re.IGNORECASE)
            cell_match = re.search(cell_name_pattern, text, re.IGNORECASE)

            kclb_number = kclb_match.group(1).strip() if kclb_match else None
            cell_name = cell_match.group(1).strip() if cell_match else None

            return {"cell_name": cell_name, "kclb_number": kclb_number}

        except AttributeError:  # 정규식 매칭 실패 시
            logging.warning("KCLB Number 또는 Cell Name을 찾을 수 없습니다.")
            return {"cell_name": None, "kclb_number": None}
        except Exception as e:
            logging.error(f"Cell 및 KCLB 추출 중 오류: {e}")
            return {"cell_name": None, "kclb_number": None}

    @staticmethod
    def generate_report(extracted_texts: List[str], output_path: str = "report.txt", encoding: str = "utf-8") -> None:
        """OCR 결과 기반으로 보고서 생성."""
        if not extracted_texts:
            logging.warning("보고서 생성을 위한 텍스트가 제공되지 않았습니다.") # 경고 로그로 변경
            return

        try:
            with open(output_path, "w", encoding=encoding) as file:
                for i, text in enumerate(extracted_texts):
                    file.write(f"--- Document {i + 1} ---\n{text}\n\n")
            logging.info(f"보고서가 {output_path}에 저장되었습니다.")
        except (IOError, OSError) as e:
            logging.error(f"보고서 생성 중 오류: {e}")
            raise  # 오류를 다시 발생시켜 상위에서 처리하도록 함