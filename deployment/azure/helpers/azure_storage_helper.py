"""
Azure Blob Storage helper for AlphaChess
用于在 Azure 环境中存储和加载模型、数据文件
"""

import os
from typing import Optional
from pathlib import Path


class AzureBlobHelper:
    """Azure Blob Storage 辅助类"""
    
    def __init__(
        self,
        account_name: Optional[str] = None,
        account_key: Optional[str] = None,
        connection_string: Optional[str] = None
    ):
        """
        初始化 Azure Blob 客户端
        
        Args:
            account_name: 存储账户名（或从环境变量 AZURE_STORAGE_ACCOUNT 读取）
            account_key: 存储密钥（或从环境变量 AZURE_STORAGE_KEY 读取）
            connection_string: 连接字符串（或从环境变量 AZURE_STORAGE_CONNECTION_STRING 读取）
        """
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            raise ImportError(
                "请安装 Azure Storage SDK: pip install azure-storage-blob"
            )
        
        # 优先使用连接字符串
        conn_str = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        
        if conn_str:
            self.blob_service_client = BlobServiceClient.from_connection_string(conn_str)
        else:
            # 使用账户名和密钥
            acc_name = account_name or os.getenv("AZURE_STORAGE_ACCOUNT")
            acc_key = account_key or os.getenv("AZURE_STORAGE_KEY")
            
            if not acc_name or not acc_key:
                raise ValueError(
                    "必须提供 connection_string 或 (account_name + account_key)"
                )
            
            account_url = f"https://{acc_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=acc_key
            )
    
    def upload_file(
        self,
        local_path: str,
        container_name: str,
        blob_name: Optional[str] = None,
        overwrite: bool = True
    ) -> str:
        """
        上传文件到 Blob Storage
        
        Args:
            local_path: 本地文件路径
            container_name: 容器名（如 'models', 'data'）
            blob_name: Blob 名称（默认使用文件名）
            overwrite: 是否覆盖已存在的文件
            
        Returns:
            Blob URL
        """
        if blob_name is None:
            blob_name = Path(local_path).name
        
        container_client = self.blob_service_client.get_container_client(container_name)
        
        # 确保容器存在
        try:
            container_client.create_container()
        except Exception:
            pass  # 容器已存在
        
        blob_client = container_client.get_blob_client(blob_name)
        
        with open(local_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=overwrite)
        
        return blob_client.url
    
    def download_file(
        self,
        container_name: str,
        blob_name: str,
        local_path: str
    ) -> str:
        """
        从 Blob Storage 下载文件
        
        Args:
            container_name: 容器名
            blob_name: Blob 名称
            local_path: 本地保存路径
            
        Returns:
            本地文件路径
        """
        container_client = self.blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        
        # 确保本地目录存在
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(local_path, "wb") as f:
            download_stream = blob_client.download_blob()
            f.write(download_stream.readall())
        
        return local_path
    
    def list_blobs(self, container_name: str, prefix: Optional[str] = None) -> list:
        """
        列出容器中的 Blob
        
        Args:
            container_name: 容器名
            prefix: 前缀过滤（如 'models/v1'）
            
        Returns:
            Blob 名称列表
        """
        container_client = self.blob_service_client.get_container_client(container_name)
        
        blobs = container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blobs]
    
    def delete_blob(self, container_name: str, blob_name: str):
        """删除 Blob"""
        container_client = self.blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.delete_blob()
    
    def get_model_path(self, model_name: str = "latest.pt", cache_dir: str = "/tmp/models") -> str:
        """
        获取模型路径（自动从 Blob 下载并缓存）
        
        Args:
            model_name: 模型文件名
            cache_dir: 本地缓存目录
            
        Returns:
            本地模型路径
        """
        local_path = os.path.join(cache_dir, model_name)
        
        # 如果本地不存在，从 Blob 下载
        if not os.path.exists(local_path):
            print(f"从 Azure Blob 下载模型: {model_name}")
            self.download_file("models", model_name, local_path)
        
        return local_path


# 使用示例
if __name__ == "__main__":
    # 初始化
    blob_helper = AzureBlobHelper()
    
    # 上传模型
    # blob_helper.upload_file("models/latest.pt", "models", "latest.pt")
    
    # 下载模型
    # blob_helper.download_file("models", "latest.pt", "/tmp/latest.pt")
    
    # 列出所有模型
    # models = blob_helper.list_blobs("models")
    # print(f"可用模型: {models}")
    
    # 获取模型路径（自动下载）
    # model_path = blob_helper.get_model_path("latest.pt")
    # print(f"模型路径: {model_path}")
    
    print("Azure Blob Storage Helper 已就绪")

