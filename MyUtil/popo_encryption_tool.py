import base64

from Crypto.Cipher import AES
import hashlib

"""
POPO消息加解密工具
"""


class AESCipher:
    '''
    AES/CBC/PKCS5Padding
    '''

    def __init__(self, aesKey):
        key = aesKey[:16]
        iv = aesKey[16:]
        # 秘钥
        self.key = key.encode()
        # 偏移量
        self.iv = iv.encode()

    def aes_cbc_encrypt(self, text):
        """
        AES/CBC/PKCS5Padding 加密
        """
        BLOCK_SIZE = AES.block_size
        # 需要加密的文件，不足BLOCK_SIZE的补位(text可能是含中文，而中文字符utf-8编码占3个位置,gbk是2，所以需要以len(text.encode())，而不是len(text)计算补码)
        text = text + (BLOCK_SIZE - len(text.encode()) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(text.encode()) % BLOCK_SIZE)
        # 创建一个aes对象 key 秘钥 mdoe 定义模式 iv#偏移量--必须16字节
        cipher = AES.new(key=self.key, mode=AES.MODE_CBC, IV=self.iv)
        # 利用AES对象进行加密
        encrypted_text = cipher.encrypt(text.encode())

        return base64.b64encode(encrypted_text).decode('utf-8')

    def aes_cbc_decrypt(self, encrypted_text):
        """
        AES/CBC/PKCS5Padding 解密
        """
        if not encrypted_text:
            raise ValueError("加密文本不能为空")
        try:
            encrypted_text = base64.b64decode(encrypted_text)
            # 创建一个aes对象 key 秘钥 mdoe 定义模式 iv#偏移量--必须16字节
            cipher = AES.new(key=self.key, mode=AES.MODE_CBC, IV=self.iv)
            # 利用AES对象进行解密
            decrypted_text = cipher.decrypt(encrypted_text)
            # 去除补位
            dec_res = decrypted_text[:-ord(decrypted_text[len(decrypted_text) - 1:])]
            return dec_res.decode()
        except Exception as e:
            raise

    def popo_check_signature(self, token: str, timestamp, nonce, signature):
        temp_data_dict = {
            'token': token,
            'timestamp': timestamp,
            'nonce': nonce
        }
        sorted_data = sorted(temp_data_dict.items(), key=lambda x: x[1])
        data = ''
        for k, v in sorted_data:
            data += v
        hash_object = hashlib.sha256()
        hash_object.update(data.encode())
        hash_value = hash_object.hexdigest()

        return hash_value == signature


if __name__ == "__main__":
    # 示例：创建AESCipher实例
    aesKey = "PFPsJJk5AnYEJwcXHeDdwBm6f2AQCsGF"  # 必须是32个字符，前16个用于秘钥，后16个用于IV
    aes_cipher = AESCipher(aesKey)

    # 示例：加密文本
    original_text = "success"
    encrypted_text = aes_cipher.aes_cbc_encrypt(original_text)
    print(f"加密后的文本: {encrypted_text}")

    # 示例：解密文本
    decrypted_text = aes_cipher.aes_cbc_decrypt(encrypted_text)
    print(f"解密后的文本: {decrypted_text}")
