#embedding_utils.py
import logging
import json
import numpy as np
import os
from typing import Dict, List, Optional
from sentence_transformers import SentenceTransformer
from Settings.settings_manager import SettingsManager

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)

class EmbeddingUtils:
    @staticmethod
    def load_embedding_model(model_name: str = "nlpai-lab/KoE5", local_model_path: Optional[str] = None) -> SentenceTransformer:
        """임베딩 모델을 로드합니다."""
        try:
            if local_model_path and os.path.exists(local_model_path):
                logging.info(f"로컬 모델 로드 완료. 경로: {local_model_path}")
                return SentenceTransformer(local_model_path)
            else:
                logging.info(f"{model_name} 모델 로드 시도.")
                return SentenceTransformer(model_name)
        except Exception as e:
            logging.error(f"모델 로드 중 오류 발생: {e}")
            raise RuntimeError(f"임베딩 모델 로드 실패: {e}")

    @staticmethod
    def generate_document_type_embeddings(settings_manager: SettingsManager, local_model_path: Optional[str] = None) -> Dict[str, List[float]]:
        """문서 유형별 임베딩을 생성합니다."""
        try:
            model = EmbeddingUtils.load_embedding_model(local_model_path=local_model_path)
            document_types_path = settings_manager.get_setting_path("document_types_path")
            document_embedding_path = settings_manager.get_setting_path("document_embedding_path")

            if not document_types_path:
                raise ValueError("document_types_path가 설정되지 않았습니다.")
            if not document_embedding_path:
                raise ValueError("document_embedding_path가 설정되지 않았습니다.")

            with open(document_types_path, "r", encoding="utf-8") as f:
                document_types: Dict[str, List[str]] = json.load(f)

            embeddings: Dict[str, List[float]] = {}
            for doc_type, texts in document_types.items():
                if not texts:
                    logging.warning(f"{doc_type}에 대한 텍스트가 없습니다.")
                    embeddings[doc_type] = []
                    continue

                encoded_texts = model.encode(texts)

                if encoded_texts is None or encoded_texts.size == 0:
                    logging.warning(f"{doc_type} 인코딩 결과가 없습니다. 빈 임베딩으로 처리합니다.")
                    embeddings[doc_type] = []
                    continue
                
                embeddings[doc_type] = np.mean(encoded_texts, axis=0).tolist()

            with open(document_embedding_path, "w", encoding="utf-8") as f:
                json.dump(embeddings, f, indent=4, ensure_ascii=False)

            logging.info("문서 유형 임베딩 생성 완료.")
            return embeddings

        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            logging.error(f"파일 또는 설정 처리 오류: {e}")
            raise
        except RuntimeError as e:
            logging.error(f"임베딩 모델 로드 실패: {e}")
            raise
        except Exception as e:
            logging.exception(f"임베딩 생성 중 오류 발생: {e}")
            raise

    @staticmethod
    def run_embedding_generation(settings_manager: SettingsManager, local_model_path: Optional[str] = None):
        try:
            EmbeddingUtils.generate_document_type_embeddings(settings_manager, local_model_path)
            logging.info("임베딩 생성 작업 완료.")
        except KeyError:
            logging.error("SettingsManager가 초기화되지 않았습니다. config 파일을 확인해주세요.")
        except Exception as e:
            logging.exception(f"임베딩 생성 작업 중 오류 발생: {e}")
