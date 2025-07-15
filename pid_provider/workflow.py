import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional


class DocumentIDError(Exception):
    """Exceção personalizada para erros do sistema de ID de documentos."""

    pass


@dataclass
class Document:
    """Representa um documento com seus metadados."""

    id: str
    metadata: Dict[str, Any]

    def __hash__(self):
        # Para permitir uso em sets, baseado nos metadados
        return hash(str(sorted(self.metadata.items())))


class DocumentIDSystem:
    """Sistema para gerenciar IDs únicos de documentos."""

    def __init__(self):
        # Armazena documentos por ID
        self.documents: Dict[str, Document] = {}
        # Índice reverso: hash dos metadados -> ID (para busca rápida)
        self.metadata_index: Dict[int, str] = {}

    def _generate_unique_id(self) -> str:
        """Gera um ID único que não existe no sistema."""
        while True:
            new_id = str(uuid.uuid4())
            if new_id not in self.documents:
                return new_id

    def _get_metadata_hash(self, metadata: Dict[str, Any]) -> int:
        """Calcula hash dos metadados para comparação."""
        return hash(str(sorted(metadata.items())))

    def _document_exists_with_metadata(self, metadata: Dict[str, Any]) -> Optional[str]:
        """Verifica se já existe documento com os mesmos metadados."""
        metadata_hash = self._get_metadata_hash(metadata)
        return self.metadata_index.get(metadata_hash)

    def process_document(
        self, metadata: Dict[str, Any], document_id: Optional[str] = None
    ) -> str:
        """
        Processa um documento e retorna seu ID.

        Args:
            metadata: Metadados do documento
            document_id: ID opcional do documento

        Returns:
            str: ID do documento (gerado ou fornecido)

        Raises:
            DocumentIDError: Se houver conflito de IDs
        """
        # PRIMEIRO: Verificar se documento já está registrado pelos metadados
        existing_id = self._document_exists_with_metadata(metadata)

        if existing_id is not None:
            # Documento já existe no sistema
            if document_id == existing_id:
                # Caso 2: ID fornecido coincide com registrado - OK
                return existing_id
            elif document_id is None:
                # Caso 1: Sem ID fornecido - retornar ID existente
                return existing_id
            else:
                # Caso 3: ID fornecido é diferente do registrado - erro
                raise DocumentIDError(
                    f"Documento já registrado com ID '{existing_id}', "
                    f"mas foi fornecido ID divergente '{document_id}'"
                )

        # Documento NÃO existe no sistema
        if document_id is None:
            # Caso 4: Sem ID fornecido - gerar novo
            new_id = self._generate_unique_id()
            self._register_document(new_id, metadata)
            return new_id

        # Caso 5: ID fornecido - verificar se está disponível
        if document_id in self.documents:
            # ID já usado por outro documento
            raise DocumentIDError(
                f"ID '{document_id}' já está sendo usado por outro documento"
            )

        # Caso 6: ID fornecido está disponível - usar
        self._register_document(document_id, metadata)
        return document_id

    def _register_document(self, doc_id: str, metadata: Dict[str, Any]) -> None:
        """Registra um documento no sistema."""
        document = Document(id=doc_id, metadata=metadata)
        self.documents[doc_id] = document
        metadata_hash = self._get_metadata_hash(metadata)
        self.metadata_index[metadata_hash] = doc_id

    def replace_document_id(self, old_id: str, new_id: str) -> str:
        """
        Função extra: Substitui um ID existente por um novo ID inédito.

        Args:
            old_id: ID atual do documento
            new_id: Novo ID desejado

        Returns:
            str: O novo ID confirmado

        Raises:
            DocumentIDError: Se o documento não existir ou novo ID já estiver em uso
        """
        # Verificar se o documento com old_id existe
        if old_id not in self.documents:
            raise DocumentIDError(f"Documento com ID '{old_id}' não encontrado")

        # Verificar se o novo ID é realmente inédito
        if new_id in self.documents:
            raise DocumentIDError(
                f"Novo ID '{new_id}' já está sendo usado por outro documento"
            )

        # Realizar a substituição
        document = self.documents[old_id]

        # Remover o registro antigo
        del self.documents[old_id]
        metadata_hash = self._get_metadata_hash(document.metadata)

        # Adicionar com novo ID
        document.id = new_id
        self.documents[new_id] = document
        self.metadata_index[metadata_hash] = new_id

        return new_id

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Retorna um documento pelo ID."""
        return self.documents.get(doc_id)

    def list_documents(self) -> Dict[str, Document]:
        """Retorna todos os documentos registrados."""
        return self.documents.copy()


# Exemplo de uso
if __name__ == "__main__":
    # Inicializar sistema
    system = DocumentIDSystem()

    # Exemplo 1: Documento sem ID fornecido (novo documento)
    metadata1 = {"title": "Documento A", "author": "João", "type": "relatório"}
    id1 = system.process_document(metadata1)
    print(f"Documento 1 - ID gerado: {id1}")

    # Exemplo 2: Mesmo documento sem ID (deve retornar ID existente)
    try:
        id1_repeat = system.process_document(metadata1)
        print(f"Documento 1 repetido - ID existente: {id1_repeat}")
        print(f"IDs são iguais: {id1 == id1_repeat}")
    except DocumentIDError as e:
        print(f"Erro: {e}")

    # Exemplo 3: Mesmo documento com ID correto
    try:
        id1_with_correct_id = system.process_document(metadata1, id1)
        print(f"Documento 1 com ID correto: {id1_with_correct_id}")
    except DocumentIDError as e:
        print(f"Erro: {e}")

    # Exemplo 4: Mesmo documento com ID DIVERGENTE (deve dar erro)
    try:
        id1_with_wrong_id = system.process_document(metadata1, "ID-ERRADO")
        print(f"Documento 1 com ID errado: {id1_with_wrong_id}")
    except DocumentIDError as e:
        print(f"Erro: {e}")

    # Exemplo 5: Novo documento com ID fornecido (inédito)
    metadata2 = {"title": "Documento B", "author": "Maria", "type": "artigo"}
    try:
        id2 = system.process_document(metadata2, "DOC-001")
        print(f"Documento 2 - ID fornecido: {id2}")
    except DocumentIDError as e:
        print(f"Erro: {e}")

    # Exemplo 6: Novo documento tentando usar ID já ocupado (erro)
    try:
        metadata3 = {"title": "Documento C", "author": "Pedro", "type": "manual"}
        id3 = system.process_document(metadata3, "DOC-001")
        print(f"Documento 3 - ID: {id3}")
    except DocumentIDError as e:
        print(f"Erro: {e}")

    # Exemplo 7: Substituir ID (função extra)
    try:
        new_id = system.replace_document_id("DOC-001", "DOC-001-NOVO")
        print(f"ID substituído com sucesso: {new_id}")
    except DocumentIDError as e:
        print(f"Erro na substituição: {e}")

    # Listar todos os documentos
    print("\nDocumentos registrados:")
    for doc_id, doc in system.list_documents().items():
        print(f"  {doc_id}: {doc.metadata['title']}")

    # Exemplo 8: Verificar se documento B ainda funciona após mudança de ID
    try:
        id2_check = system.process_document(metadata2, "DOC-001-NOVO")
        print(f"Documento 2 após mudança de ID: {id2_check}")
    except DocumentIDError as e:
        print(f"Erro: {e}")
