# Bài thuyết trình và bảo vệ đề cương hoàn chỉnh

## Tên đề tài

**Nghiên cứu và xây dựng hệ thống dự đoán giá bất động sản theo khu vực bằng học máy kết hợp dữ liệu IoT từ điện thoại thông minh**

---

## 1. Bài thuyết trình hoàn chỉnh để nói trước hội đồng

Kính thưa thầy/cô hội đồng, kính thưa giảng viên hướng dẫn, cùng toàn thể các bạn.

Nhóm chúng em xin trình bày đề cương của đề tài: **Nghiên cứu và xây dựng hệ thống dự đoán giá bất động sản theo khu vực bằng học máy kết hợp dữ liệu IoT từ điện thoại thông minh**.

Trong phần trình bày này, chúng em sẽ lần lượt đi qua các nội dung chính gồm: lý do chọn đề tài, mục tiêu nghiên cứu, cơ sở khoa học và các tài liệu tham khảo liên quan, phương pháp thực hiện, những kết quả nhóm đã làm được đến thời điểm hiện tại, các điểm còn hạn chế, phần đang cải tiến, và cuối cùng là định hướng hoàn thiện trong giai đoạn tiếp theo.

Trước hết, về **lý do chọn đề tài**, nhóm nhận thấy rằng bài toán định giá bất động sản là một bài toán có tính ứng dụng rất cao trong thực tế. Trong thị trường hiện nay, giá bất động sản phụ thuộc vào rất nhiều yếu tố như vị trí, diện tích, loại hình tài sản, tình trạng pháp lý, tiện ích xung quanh, chất lượng môi trường sống và mức độ phát triển của khu vực. Tuy nhiên, trên thực tế, việc định giá vẫn thường phụ thuộc khá nhiều vào kinh nghiệm chủ quan của con người, hoặc dựa trên các tin đăng có tính tham khảo nhưng chưa được xác minh đầy đủ.

Điều này dẫn đến ba vấn đề lớn. Thứ nhất, giá tham khảo giữa các nguồn có thể chênh lệch đáng kể. Thứ hai, quá trình thu thập và đối chiếu dữ liệu mất nhiều thời gian. Thứ ba, các yếu tố môi trường thực địa như độ ồn, vị trí GPS, điều kiện hiện trường thường chưa được đưa vào mô hình một cách có hệ thống. Từ đó, nhóm lựa chọn hướng tiếp cận xây dựng một hệ thống AVM, tức là hệ thống định giá bất động sản tự động, kết hợp với dữ liệu IoT thu từ điện thoại thông minh nhằm tăng tính thực tiễn và khả năng mở rộng cho bài toán.

Tiếp theo là **mục tiêu của đề tài**.

Mục tiêu tổng quát của đề tài là xây dựng một hệ thống hỗ trợ dự đoán giá bất động sản theo khu vực dựa trên học máy, đồng thời kết hợp các dữ liệu IoT thu từ điện thoại thông minh để bổ sung thông tin về điều kiện môi trường tại hiện trường.

Từ mục tiêu tổng quát đó, nhóm đặt ra các mục tiêu cụ thể như sau.

Thứ nhất, xây dựng được một cơ sở dữ liệu bất động sản có cấu trúc, bao gồm dữ liệu từ nguồn công khai và dữ liệu nhóm tự thu thập.

Thứ hai, thiết kế được quy trình quản lý dữ liệu có truy vết nguồn gốc, có trạng thái xác minh, có lưu thông tin nguồn, thời điểm thu thập và lịch sử thay đổi.

Thứ ba, xây dựng mô hình học máy để dự đoán giá bất động sản trên cơ sở các đặc trưng như loại hình bất động sản, khu vực, diện tích, số phòng, pháp lý, nội thất, toạ độ, cùng với một số biến IoT như độ ồn, nhiệt độ, độ ẩm và GPS.

Thứ tư, phát triển một hệ thống phần mềm gồm backend, frontend và giao diện thao tác để người dùng có thể nhập dữ liệu, xem thống kê, dự đoán giá và kiểm tra nguồn gốc của dữ liệu.

Thứ năm, đối chiếu kết quả của nhóm với các công trình nghiên cứu có tính học thuật, có ISBN hoặc thuộc các tạp chí, nhà xuất bản được sử dụng rộng rãi trong môi trường Scopus, ISI hoặc Web of Science.

Nếu nói riêng về **mục tiêu của chức năng dự đoán**, nhóm xác định mục tiêu này không chỉ là sinh ra một con số giá. Mục tiêu đúng của chức năng dự đoán là giúp người dùng nhận được một kết quả có thể tin cậy ở mức tham khảo, có thể kiểm chứng lại, có thể giải thích được và có thể đối chiếu với dữ liệu thực tế trên thị trường.

Nói cách khác, một kết quả dự đoán tốt trong đề tài này phải trả lời được bốn câu hỏi. Thứ nhất, giá dự đoán là bao nhiêu. Thứ hai, vì sao hệ thống đưa ra mức giá đó. Thứ ba, hệ thống dựa trên dữ liệu nào để đưa ra kết quả. Thứ tư, mức độ tin cậy của kết quả đến đâu. Nếu không trả lời được bốn câu hỏi này thì hệ thống có thể dự đoán được, nhưng chưa đủ sức thuyết phục đối với người dùng thực tế.

Về **câu hỏi nghiên cứu**, đề tài tập trung trả lời ba câu hỏi chính.

Câu hỏi thứ nhất là: liệu mô hình học máy có thể hỗ trợ dự đoán giá bất động sản theo khu vực với độ chính xác chấp nhận được trên bộ dữ liệu mà nhóm xây dựng hay không.

Câu hỏi thứ hai là: việc bổ sung dữ liệu IoT từ điện thoại thông minh có tiềm năng nâng cao chất lượng dự đoán và tăng tính thực tế của hệ thống hay không.

Câu hỏi thứ ba là: làm thế nào để xây dựng được một hệ thống vừa có giá trị kỹ thuật, vừa có tính học thuật, vừa đảm bảo minh bạch về nguồn dữ liệu và khả năng mở rộng trong tương lai.

Sau phần mục tiêu, nhóm xin trình bày **cơ sở khoa học và tổng quan nghiên cứu liên quan**.

Về nền tảng lý thuyết cho học máy hồi quy, nhóm tham khảo sách *Statistical Learning from a Regression Perspective* của Springer. Đây là tài liệu có ISBN rõ ràng và cung cấp nền tảng về supervised learning, hồi quy, đánh giá mô hình, cũng như mối quan hệ giữa độ lệch, phương sai và khả năng khái quát hóa.

Về nền tảng chuyên sâu hơn cho lĩnh vực định giá tự động, nhóm tham khảo sách *Advances in Automated Valuation Modeling*, cũng do Springer xuất bản và có ISBN rõ ràng. Tài liệu này giúp nhóm định vị đề tài trong bối cảnh rộng hơn của AVM, mass appraisal và các hướng đánh giá tài sản bằng dữ liệu lớn.

Về các nghiên cứu gần với đề tài, nhóm tham khảo một số bài báo liên quan đến dự báo giá bất động sản bằng học máy. Chẳng hạn, bài của Choy và Ho công bố trên tạp chí *Land* năm 2023 cho thấy các mô hình học máy có thể cải thiện khả năng dự đoán so với các phương pháp truyền thống trong bài toán bất động sản. Một nghiên cứu khác của Mora-Garcia và cộng sự trên *Land* năm 2022 cũng chỉ ra vai trò quan trọng của việc lựa chọn đặc trưng và chất lượng dữ liệu trong dự báo giá nhà đất.

Về hướng tích hợp dữ liệu cảm biến từ điện thoại thông minh, nhóm tham khảo các nghiên cứu trên tạp chí *Sensors*, trong đó có các công trình liên quan đến thu thập dữ liệu âm thanh, mobile crowdsensing và độ tin cậy của cảm biến từ thiết bị di động. Những tài liệu này là cơ sở để nhóm giải thích vì sao biến như mức độ ồn, dữ liệu GPS hoặc điều kiện môi trường có thể được xem như những tín hiệu bổ sung phục vụ đánh giá giá trị bất động sản.

Ngoài ra, nhóm cũng tham khảo các nghiên cứu gần đây về AVM theo hướng giải thích được và lượng hóa bất định, ví dụ như các công trình trên *Journal of Real Estate Finance and Economics* và *Journal of Property Research*. Các tài liệu này đặc biệt hữu ích để nhóm định hướng phần giải thích mô hình, mức độ tin cậy của dự đoán, và cách trình bày kết quả theo hướng học thuật thay vì chỉ dừng lại ở mức demo kỹ thuật.

Từ việc khảo sát tài liệu, nhóm nhận thấy rằng nhiều nghiên cứu đã làm tốt phần mô hình học máy, nhưng vẫn còn khoảng trống ở chỗ tích hợp đồng thời ba yếu tố: dữ liệu thị trường, dữ liệu tự thu thập có xác minh, và dữ liệu IoT thực địa từ điện thoại thông minh trong cùng một quy trình phần mềm hoàn chỉnh. Đây chính là hướng mà nhóm lựa chọn để phát triển đề tài.

Để làm rõ hơn phần đối chiếu học thuật, nhóm xin **so sánh trực tiếp với ba công trình tương tự ý tưởng** như sau.

**Công trình thứ nhất** là bài báo của **Choy và Ho** công bố trên tạp chí *Land* năm 2023, DOI: **10.3390/land12040740**. Đây là một tạp chí có mặt trong các hệ chỉ mục như Scopus và Web of Science theo thông tin từ ISSN Portal của tạp chí *Land*. Ý tưởng chính của công trình này là sử dụng học máy để dự đoán giá bất động sản từ dữ liệu giao dịch nhà ở. Bài báo sử dụng các thuật toán như **Extra Trees, k-Nearest Neighbors và Random Forest**, sau đó so sánh với mô hình hedonic truyền thống.

Nếu so với công trình này, điểm giống của đồ án là đều giải quyết bài toán dự đoán giá bất động sản bằng học máy trên dữ liệu cấu trúc. Tuy nhiên, điểm khác biệt là bài báo này chủ yếu tập trung vào độ chính xác mô hình trên dữ liệu giao dịch đã được xử lý, còn đồ án của nhóm đi theo hướng **xây dựng cả hệ thống**, trong đó dữ liệu phải đi qua bước thu thập, truy vết nguồn, xác minh và tích hợp thêm thông tin thực địa. Ngoài ra, trong bối cảnh Việt Nam, dữ liệu không phải lúc nào cũng chuẩn hóa tốt như dữ liệu học thuật, nên cách tiếp cận của nhóm phù hợp hơn ở chỗ chấp nhận sự không đồng nhất của dữ liệu và tổ chức lại nó ở mức hệ thống.

**Công trình thứ hai** là bài báo của **Deppner, von Ahlefeldt-Dehn, Beracha và cộng sự** trên *The Journal of Real Estate Finance and Economics*, DOI: **10.1007/s11146-023-09944-1**. Đây là nghiên cứu về việc nâng cao độ chính xác của định giá bất động sản thương mại bằng **boosting trees** theo hướng có thể giải thích được. Công trình này đặc biệt quan tâm đến tính chính xác và tính giải thích của mô hình, tức là không chỉ dự đoán tốt mà còn cần giảm sai lệch cấu trúc trong định giá.

Điểm giống giữa công trình này và đồ án của nhóm là cùng quan tâm đến hướng **học máy có giải thích**, đặc biệt là vai trò của boosting trong hệ thống AVM. Tuy nhiên, khác biệt nằm ở bối cảnh áp dụng. Công trình này dựa trên dữ liệu bất động sản thương mại tại Mỹ, nơi dữ liệu thể chế, dữ liệu đầu vào và chuẩn định giá đã tương đối phát triển. Trong khi đó, đồ án của nhóm hướng tới bối cảnh Việt Nam, nơi dữ liệu phân tán hơn, mức độ đồng nhất thấp hơn và việc thu thập dữ liệu thực địa có vai trò lớn hơn. Vì vậy, thay vì chỉ tập trung vào mô hình boosting, đồ án của nhóm phải giải bài toán rộng hơn là **làm sao đưa dữ liệu thực tế của Việt Nam vào một pipeline có thể vận hành được**.

**Công trình thứ ba** là bài báo của **Zuo và cộng sự** trên tạp chí *Sensors* năm 2016, DOI: **10.3390/s16101692**, với chủ đề lập bản đồ tiếng ồn môi trường bằng điện thoại thông minh. *Sensors* cũng là tạp chí có chỉ mục Scopus và Web of Science theo ISSN Portal. Về bản chất, đây không phải là bài báo định giá bất động sản trực tiếp, nhưng lại rất gần với **phần IoT smartphone** trong đồ án của nhóm, vì công trình này chứng minh rằng dữ liệu cảm biến thu từ điện thoại thông minh có thể được sử dụng như một nguồn dữ liệu môi trường chi phí thấp và có ý nghĩa thực tế.

Điểm giống ở đây là cả hai cùng coi điện thoại thông minh là một thiết bị thu thập dữ liệu hiện trường. Điểm khác biệt là bài báo của Zuo chỉ tập trung vào bài toán môi trường tiếng ồn, còn đồ án của nhóm dùng dữ liệu đó như một **nhóm đặc trưng bổ sung** để hỗ trợ dự đoán giá bất động sản. Đây chính là điểm nối giữa nghiên cứu cảm biến và nghiên cứu bất động sản mà nhóm đang theo đuổi. Xét trong bối cảnh Việt Nam, hướng này đặc biệt phù hợp vì sử dụng điện thoại thông minh giúp giảm chi phí thu thập dữ liệu, không đòi hỏi hạ tầng cảm biến cố định quá lớn, và dễ triển khai trong điều kiện dữ liệu công khai còn thiếu đồng bộ.

Nếu tổng hợp ba công trình trên, có thể thấy rõ rằng đồ án của nhóm kế thừa ba hướng học thuật quan trọng. Từ công trình trên *Land*, nhóm kế thừa tư duy dùng học máy để dự đoán giá bất động sản. Từ công trình trên *The Journal of Real Estate Finance and Economics*, nhóm kế thừa tư duy về AVM theo hướng giải thích được và giảm sai lệch định giá. Từ công trình trên *Sensors*, nhóm kế thừa tư duy dùng điện thoại thông minh như một thiết bị IoT để tạo ra lớp dữ liệu môi trường thực địa.

Tuy nhiên, **tính khác biệt cốt lõi** của đồ án nằm ở chỗ nhóm không sao chép riêng lẻ bất kỳ công trình nào, mà đang cố gắng kết hợp ba hướng đó thành một hệ thống phù hợp với Việt Nam. Nghĩa là, đồ án không chỉ hỏi “mô hình nào tốt”, mà còn hỏi “dữ liệu ở Việt Nam lấy từ đâu, tin cậy đến mức nào, ai xác minh, điều kiện môi trường có ảnh hưởng không, và kết quả dự đoán có giải thích được hay không”.

Chính vì vậy, nếu hội đồng yêu cầu một câu kết luận ngắn cho phần so sánh, nhóm có thể phát biểu như sau: **các bài báo tham khảo chủ yếu mạnh ở từng mảnh riêng lẻ như độ chính xác mô hình, tính giải thích hoặc thu thập dữ liệu cảm biến; còn đồ án của nhóm cố gắng tích hợp các mảnh đó thành một kiến trúc ứng dụng hoàn chỉnh, và đây là điểm làm cho đề tài phù hợp hơn với bối cảnh bất động sản Việt Nam**.

Ngoài ba công trình trên, nhóm còn sử dụng thêm một **nguồn sách học thuật có ISBN** là *Advances in Automated Valuation Modeling* của Springer, DOI: **10.1007/978-3-319-49746-4**. Nguồn này không phải là một dự án thực nghiệm đơn lẻ, nhưng lại rất quan trọng vì cung cấp khung lý thuyết về AVM, mass appraisal và cách nhìn hệ thống trong định giá tự động. Nhóm sử dụng tài liệu này để làm nền tảng học thuật cho phần kiến trúc hệ thống và định vị đề tài trong đúng hướng nghiên cứu AVM hiện đại.

Tiếp theo, nhóm xin trình bày **đối tượng và phạm vi nghiên cứu**.

Đối tượng nghiên cứu của đề tài là các bản ghi bất động sản thuộc nhiều loại hình như nhà phố, căn hộ, đất, nhà liền kề và biệt thự. Về phạm vi dữ liệu, hệ thống hiện đang xử lý dữ liệu trên nhiều tỉnh, thành phố và quận, huyện khác nhau. Về mặt kỹ thuật, đề tài tập trung vào bài toán hồi quy để dự đoán giá, chưa đi sâu vào dự báo chuỗi thời gian dài hạn hay phân tích chính sách vĩ mô của thị trường bất động sản.

Về **phương pháp thực hiện**, nhóm triển khai đề tài theo quy trình gồm các bước chính.

Bước thứ nhất là thiết kế cơ sở dữ liệu và chuẩn hóa thông tin bản ghi bất động sản. Trong đó, nhóm lưu đầy đủ thông tin về nguồn dữ liệu, loại nguồn, tình trạng xác minh, trạng thái bản ghi, thời điểm thu thập và các trường liên quan đến thu thập thực địa.

Bước thứ hai là xây dựng hệ thống backend bằng FastAPI để phục vụ các API cho dự đoán, thống kê, quản lý dữ liệu, quản lý nguồn dữ liệu, lưu ảnh và thu thập dữ liệu IoT.

Bước thứ ba là xây dựng frontend bằng React để hỗ trợ nhập dữ liệu, dự đoán giá, xem dashboard, xem chi tiết nguồn dữ liệu, và kiểm tra các bản ghi tự thu thập.

Bước thứ tư là xây dựng pipeline học máy để huấn luyện và đánh giá các mô hình như RandomForest, GradientBoosting và XGBoost.

Bước thứ năm là so sánh các mô hình theo các chỉ số như MAE, RMSE và R bình phương, từ đó xác định hướng lựa chọn mô hình phù hợp hơn cho giai đoạn triển khai chính thức.

Bước thứ sáu là lưu version mô hình, truy vết quá trình huấn luyện và chuẩn bị cho việc giải thích dự đoán cũng như mở rộng về sau.

Nếu mô tả rõ hơn về **mô hình kiến trúc hệ thống**, đề tài của nhóm được xây dựng theo kiến trúc ba lớp.

Lớp thứ nhất là **lớp dữ liệu**. Ở lớp này, hệ thống lưu thông tin bất động sản, nguồn dữ liệu, trạng thái xác minh, dữ liệu IoT, lịch sử dự đoán, version mô hình và audit log. Điểm quan trọng là dữ liệu không chỉ lưu để dự đoán, mà còn lưu để truy vết nguồn và quản lý chất lượng dữ liệu.

Lớp thứ hai là **lớp xử lý nghiệp vụ và trí tuệ nhân tạo**. Lớp này do backend FastAPI và pipeline học máy đảm nhiệm. Backend chịu trách nhiệm tiếp nhận dữ liệu từ người dùng, kiểm tra hợp lệ, điều phối các API và trả kết quả dự đoán. Pipeline học máy chịu trách nhiệm tiền xử lý dữ liệu, tạo đặc trưng, huấn luyện mô hình, đánh giá mô hình, lưu version và nạp lại mô hình khi cần dự đoán.

Lớp thứ ba là **lớp giao diện người dùng**. Lớp này được xây dựng bằng React và cung cấp các chức năng như nhập thông tin bất động sản, xem dashboard, xem nguồn dữ liệu, quản lý bản ghi, thu thập dữ liệu tại hiện trường và xem kết quả dự đoán. Cách tổ chức này phù hợp với một hệ thống có thể phát triển về sau, vì frontend, backend và mô hình có thể cải tiến tương đối độc lập nhưng vẫn kết nối được với nhau.

Nếu nói riêng về **kiến trúc dự đoán**, luồng xử lý có thể mô tả như sau. Người dùng nhập thông tin bất động sản trên giao diện. Thông tin này được gửi lên backend. Backend lấy mô hình đã huấn luyện, chuẩn hóa dữ liệu đầu vào theo đúng cấu trúc của quá trình train, sau đó đưa qua pipeline để sinh dự đoán. Sau khi có giá dự đoán, hệ thống còn trả về khoảng tin cậy tương đối, các bất động sản so sánh gần nhất, và phần giải thích theo mức độ ảnh hưởng của đặc trưng. Nếu trong một tình huống nào đó mô hình học máy không trả được kết quả ổn định, hệ thống còn có cơ chế dự phòng theo hướng **comparable-based**, tức là dùng các mẫu bất động sản tương đồng để ước lượng giá.

Nếu trình bày cụ thể hơn, **quy trình dự đoán bắt buộc** trong hệ thống nên đi qua các bước sau.

Bước một là người dùng nhập thông tin đầu vào, gồm loại bất động sản, tỉnh hoặc thành phố, quận huyện, diện tích, số phòng, tình trạng pháp lý, nội thất và các thông tin vị trí cơ bản.

Bước hai là hệ thống tiếp nhận và kiểm tra hợp lệ dữ liệu, ví dụ kiểm tra diện tích phải dương, loại tài sản phải đúng nhóm cho phép, và vị trí phải nằm trong tập khu vực mà hệ thống có thể xử lý.

Bước ba là hệ thống chuẩn hóa dữ liệu đầu vào theo đúng pipeline huấn luyện, tức là mã hóa các đặc trưng phân loại, chuẩn hóa các biến số, tính toán đặc trưng vị trí và đưa dữ liệu IoT vào nếu có.

Bước bốn là mô hình học máy thực hiện suy luận để sinh ra giá dự đoán.

Bước năm là hệ thống truy xuất các bất động sản tương đồng gần nhất theo loại tài sản, khu vực và diện tích để tạo lớp giải thích theo kiểu so sánh thị trường.

Bước sáu là hệ thống tổng hợp kết quả cuối cùng và hiển thị ra giao diện theo hướng không chỉ có giá, mà còn có thông tin hỗ trợ ra quyết định.

Về **thông tin cần hiển thị sau khi dự đoán**, để tăng tính thuyết phục cho người dùng, nhóm xác định màn hình kết quả cần có đầy đủ các thành phần sau.

Thứ nhất là **giá dự đoán tổng thể** và **giá trên mét vuông**. Đây là hai thông tin cơ bản nhất mà người dùng cần nhìn thấy đầu tiên.

Thứ hai là **khoảng giá tin cậy**, tức là mức dưới và mức trên của dự đoán. Việc hiển thị khoảng giá giúp người dùng hiểu rằng mô hình không khẳng định tuyệt đối một con số duy nhất, mà đưa ra một vùng giá hợp lý.

Thứ ba là **tên mô hình đang dùng**, ví dụ RandomForest, GradientBoosting hay mô hình so sánh tương đồng, cùng với **phiên bản mô hình** và **thời điểm huấn luyện**. Điều này làm tăng tính minh bạch kỹ thuật.

Thứ tư là **các đặc trưng quan trọng nhất ảnh hưởng đến giá**, ví dụ diện tích, khu vực, loại tài sản, pháp lý, khoảng cách tới trung tâm, hoặc tín hiệu IoT như độ ồn. Đây là phần giúp người dùng hiểu được logic của hệ thống.

Thứ năm là **danh sách bất động sản so sánh gần nhất**, bao gồm khu vực, diện tích, giá, giá trên mét vuông, nguồn dữ liệu, mức độ tương đồng và nếu có thì cả hình ảnh. Đây là phần rất thuyết phục vì người dùng luôn tin hơn khi thấy hệ thống không chỉ trả một con số trừu tượng mà còn cho thấy các mẫu tham chiếu cụ thể.

Thứ sáu là **thông tin về nguồn dữ liệu và provenance**, tức là hệ thống nên cho biết dự đoán này được hình thành dựa trên dữ liệu nào, từ những nguồn nào, có bao nhiêu bản ghi verified, tỷ lệ dữ liệu tự thu thập là bao nhiêu và phương pháp xử lý là gì.

Thứ bảy là **thông tin về thuật toán và tiền xử lý**, ví dụ mô hình sử dụng thuật toán nào, dữ liệu đã qua chuẩn hóa ra sao, và tập đặc trưng nào được dùng để dự đoán. Đây là lớp thông tin rất quan trọng khi người dùng là người có chuyên môn hoặc khi hệ thống cần phục vụ mục đích học thuật.

Thứ tám là **trích dẫn hoặc mô tả ngắn về phương pháp**, tức là kết quả nên có một đoạn chú thích cho biết đây là kết quả từ hệ thống AVM, dựa trên mô hình nào, phiên bản nào và dữ liệu huấn luyện thuộc giai đoạn nào. Điều này giúp tăng tính tin cậy và tính chuyên nghiệp của sản phẩm.

Như vậy, **mục tiêu hướng tới của chức năng dự đoán** không chỉ là “dự đoán đúng”, mà là “dự đoán có thể giải thích, có thể kiểm tra và có thể thuyết phục người dùng”. Đây chính là điểm mà nhóm cho rằng rất quan trọng nếu muốn đồ án có tính ứng dụng thật.

Về **các thuật toán được sử dụng**, nhóm sử dụng ba mô hình hồi quy chính là RandomForest, GradientBoosting và XGBoost.

RandomForest được dùng như một mô hình ensemble nền tảng. Điểm mạnh của nó là ổn định, ít nhạy cảm với nhiễu hơn so với nhiều mô hình khác và hoạt động khá tốt trên dữ liệu bảng có nhiều loại đặc trưng khác nhau. Trong bài toán của nhóm, RandomForest đóng vai trò là một baseline mạnh để so sánh.

GradientBoosting được sử dụng như một mô hình học tăng cường theo tuần tự. Thuật toán này học dần từ sai số của các cây trước đó, vì vậy thường phù hợp khi cần cải thiện chất lượng dự đoán trên dữ liệu cấu trúc. Trong dự án của nhóm, đây là mô hình được ưu tiên theo định hướng kỹ thuật vì phù hợp với mục tiêu tối ưu sai số của bài toán định giá.

XGBoost được đưa vào như một lựa chọn nâng cao hơn của boosting. Mục đích là để đối chiếu với hai mô hình còn lại và kiểm tra xem trên dữ liệu hiện có, mô hình boosting mạnh hơn có tạo ra cải thiện đáng kể hay không. Việc đưa XGBoost vào cũng giúp đề tài bám sát xu hướng các nghiên cứu gần đây trong bài toán dự báo trên dữ liệu bảng.

Ngoài các mô hình hồi quy chính, hệ thống còn dùng một số phương pháp kỹ thuật rất quan trọng. Trước hết là **train-test split** và **cross-validation** để đánh giá khách quan mô hình, tránh kết luận chỉ từ một lần chia dữ liệu. Tiếp theo là **chuẩn hóa dữ liệu** và **feature engineering** để biến dữ liệu thô thành đầu vào phù hợp cho mô hình học máy. Hệ thống hiện sử dụng one-hot encoding cho loại tài sản và một số khu vực trọng điểm, ánh xạ thứ bậc cho các biến như loại khu vực, pháp lý, nội thất, đồng thời tính thêm các đặc trưng vị trí như khoảng cách tới tâm đô thị bằng công thức Haversine. Ngoài ra, hệ thống còn bổ sung target encoding theo giá trung bình trên từng nhóm khu vực để tăng khả năng phản ánh mặt bằng giá theo địa phương.

Đối với phần giải thích mô hình, nhóm định hướng dùng **SHAP** để giải thích đóng góp của từng đặc trưng đối với giá dự đoán. Đây là một điểm quan trọng vì trong lĩnh vực bất động sản, mô hình không chỉ cần dự đoán đúng mà còn cần nói được vì sao lại đưa ra mức giá như vậy.

Ở đây, nhóm cũng xin làm rõ một điểm rất dễ bị nhầm về thuật ngữ. **Đồ án này hiện không huấn luyện LLM theo nghĩa mô hình ngôn ngữ lớn như ChatGPT hay các mô hình sinh văn bản**, mà đang huấn luyện **mô hình học máy hồi quy trên dữ liệu bất động sản có cấu trúc**. Nói chính xác hơn, dữ liệu sẵn có của nhóm được dùng để train các mô hình như RandomForest, GradientBoosting và XGBoost nhằm dự đoán giá. Phần AI hỗ trợ như OpenCLAW trong hệ thống hiện chỉ đóng vai trò hỗ trợ phân tích hoặc tối ưu tham số ở một số bước, chứ không phải lõi chính của mô hình dự đoán giá.

Nếu trình bày rõ về **quy trình train từ nguồn dữ liệu đã có**, nhóm thực hiện theo các bước sau.

Bước đầu tiên là lấy dữ liệu từ cơ sở dữ liệu của hệ thống. Tuy nhiên, không phải toàn bộ dữ liệu đều được đưa vào train ngay, mà nhóm lọc các bản ghi theo một số điều kiện cơ bản như phải có giá, có diện tích và ở trạng thái xác minh phù hợp để giảm nhiễu đầu vào.

Bước thứ hai là chọn các trường đặc trưng phục vụ huấn luyện. Nhóm sử dụng các trường như loại bất động sản, tỉnh thành, quận huyện, diện tích, số phòng ngủ, số phòng tắm, pháp lý, nội thất, tọa độ vị trí, cùng với các đặc trưng IoT như mức độ ồn, nhiệt độ, độ ẩm và một số đặc trưng vị trí được tính toán thêm.

Bước thứ ba là tiền xử lý dữ liệu. Ở bước này, dữ liệu thiếu được điền theo quy tắc phù hợp, các biến phân loại được mã hóa, các đặc trưng số được chuẩn hóa, và các đặc trưng vị trí hoặc ngữ cảnh được chuyển thành vector đầu vào cho mô hình. Đây là bước rất quan trọng vì trong bài toán bất động sản, chất lượng feature engineering có ảnh hưởng rất lớn đến chất lượng mô hình.

Bước thứ tư là chia dữ liệu thành tập train và tập test, sau đó huấn luyện nhiều mô hình khác nhau trên cùng một cấu hình để so sánh công bằng.

Bước thứ năm là đánh giá mô hình bằng các chỉ số như MAE, RMSE và R bình phương, đồng thời có dùng cross-validation để kiểm tra tính ổn định tương đối.

Bước thứ sáu là xác định mô hình có triển vọng phù hợp hơn, lưu version mô hình, lưu metadata huấn luyện và chuẩn bị nạp lại mô hình đó khi triển khai dự đoán trên hệ thống.

Nếu nói ngắn gọn về **thuật toán train này thực hiện như thế nào**, có thể hiểu như sau. Sau khi dữ liệu được tiền xử lý, hệ thống lần lượt đưa cùng một tập train vào các thuật toán hồi quy khác nhau. Mỗi thuật toán học một hàm ánh xạ từ đặc trưng đầu vào sang giá bất động sản. Sau đó, hệ thống đem các mô hình đã học dự đoán trên tập test để so sánh chất lượng. Mô hình nào có sai số tốt hơn và ổn định hơn sẽ được ưu tiên chọn. Nghĩa là, đây là cách huấn luyện theo hướng thực nghiệm so sánh nhiều mô hình trên cùng một bộ dữ liệu, thay vì chỉ mặc định dùng một thuật toán duy nhất ngay từ đầu.

Trong quá trình train, nhóm nhận thấy có **một số vấn đề thực tế**.

Vấn đề thứ nhất là dữ liệu bất động sản thường không đồng nhất. Cùng là một loại nhà nhưng cách ghi khu vực, pháp lý, nội thất hay mô tả hiện trạng có thể khác nhau giữa các nguồn. Điều này làm tăng độ nhiễu của dữ liệu đầu vào.

Vấn đề thứ hai là dữ liệu thiếu. Không phải bản ghi nào cũng có đủ tọa độ, pháp lý, nội thất, hay dữ liệu IoT. Nếu xử lý không tốt, mô hình sẽ học lệch hoặc mất ổn định.

Vấn đề thứ ba là dữ liệu thực địa ở Việt Nam có tính địa phương rất mạnh. Giá trị bất động sản thay đổi theo quận huyện, loại khu vực và điều kiện sống, nên nếu chỉ dùng mô hình học trên dữ liệu bảng đơn giản thì chưa đủ phản ánh khác biệt này.

Vấn đề thứ tư là khó chứng minh ngay mức đóng góp cụ thể của IoT, vì muốn chứng minh chặt chẽ thì phải có thực nghiệm đối chứng giữa nhiều bộ đặc trưng và nhiều vòng đánh giá.

Từ các vấn đề đó, nhóm đưa ra **cách giải quyết** như sau.

Thứ nhất, nhóm chuẩn hóa cấu trúc dữ liệu và quản lý nguồn dữ liệu ở mức hệ thống, thay vì chỉ thu thập xong rồi đưa thẳng vào train.

Thứ hai, nhóm sử dụng tiền xử lý và feature engineering để giảm tác động của dữ liệu thiếu, dữ liệu không đồng nhất và dữ liệu phân loại khó xử lý.

Thứ ba, nhóm không phụ thuộc vào một mô hình duy nhất, mà huấn luyện nhiều mô hình để so sánh và chọn phương án phù hợp hơn.

Thứ tư, nhóm kết hợp thêm cơ chế so sánh với các bất động sản tương đồng để tăng khả năng giải thích cho kết quả dự đoán.

Thứ năm, nhóm định hướng làm thêm các thí nghiệm đối chứng về IoT, giải thích mô hình và đánh giá độ ổn định để chuyển từ mức “có tiềm năng” sang mức “có bằng chứng định lượng rõ ràng”.

Nếu so sánh với **các đề tài và bài báo khoa học tham khảo**, có thể chia thành ba nhóm.

Nhóm thứ nhất là các nghiên cứu sử dụng dữ liệu bảng truyền thống để dự đoán giá bất động sản, ví dụ như các bài trên *Land*. Những nghiên cứu này thường mạnh ở khâu so sánh mô hình và đánh giá sai số trên dữ liệu đã được chuẩn hóa. Đề tài của nhóm kế thừa cách tiếp cận đó, nhưng đi xa hơn ở phần tổ chức hệ thống dữ liệu và truy vết nguồn.

Nhóm thứ hai là các nghiên cứu đi theo hướng giải thích mô hình, độ tin cậy dự đoán hoặc lượng hóa bất định, ví dụ các công trình trên *Journal of Real Estate Finance and Economics* và *Journal of Property Research*. Điểm mà nhóm học hỏi từ các nghiên cứu này là không xem giá dự đoán như một con số tuyệt đối, mà xem đó là kết quả cần có mức giải thích và có độ tin cậy tương đối đi kèm.

Nhóm thứ ba là các nghiên cứu về dữ liệu cảm biến, điện thoại thông minh và mobile crowdsensing trên *Sensors*. Điểm mà nhóm kế thừa ở đây là cách xem điện thoại thông minh như một nguồn dữ liệu thực địa linh hoạt. Tuy nhiên, khác với các nghiên cứu cảm biến thuần túy, đề tài của nhóm không dừng ở đo đạc môi trường, mà dùng các tín hiệu đó như đặc trưng bổ sung trong bài toán định giá bất động sản.

Từ đó, **tính khác biệt** của đồ án có thể nói ngắn gọn ở bốn ý.

Thứ nhất, đề tài không chỉ so sánh thuật toán mà còn xây dựng một kiến trúc hệ thống hoàn chỉnh gồm dữ liệu, backend, frontend và mô hình.

Thứ hai, đề tài không coi dữ liệu là một bảng số liệu tĩnh, mà là một đối tượng có nguồn gốc, có xác minh, có thể mở rộng và có thể quản trị.

Thứ ba, đề tài kết hợp dữ liệu thị trường với dữ liệu thực địa từ điện thoại thông minh, tạo ra một hướng tiếp cận gần với thực tế hơn so với các mô hình chỉ dùng dữ liệu bảng truyền thống.

Thứ tư, đề tài định hướng giải thích được mô hình, tức là không chỉ trả về giá mà còn trả về logic hình thành giá.

Về **tính phù hợp với khu vực Việt Nam**, nhóm cho rằng đây là một điểm rất quan trọng.

Thị trường bất động sản Việt Nam có một số đặc điểm riêng. Dữ liệu thường phân tán ở nhiều nguồn khác nhau, cách mô tả tài sản chưa đồng nhất, thông tin pháp lý và chất lượng môi trường sống không phải lúc nào cũng thể hiện đầy đủ trong tin đăng. Bên cạnh đó, chênh lệch giá theo khu vực ở Việt Nam rất mạnh, và ngay trong cùng một quận hay một phường, điều kiện thực tế cũng có thể khác nhau đáng kể.

Chính vì vậy, nếu chỉ áp dụng nguyên si các mô hình từ bài báo quốc tế vào bối cảnh Việt Nam mà không điều chỉnh, thì có thể sẽ không phản ánh đúng đặc thù thị trường. Hướng tiếp cận của nhóm phù hợp hơn với Việt Nam vì nhóm vừa dùng dữ liệu cấu trúc như diện tích, loại nhà, khu vực, vừa chú ý đến các tín hiệu địa phương như loại khu vực, mức độ tiếp cận tiện ích, vị trí GPS, và tiềm năng bổ sung các đặc trưng thực địa. Nói cách khác, mô hình của nhóm được định hướng để thích nghi với sự không đồng nhất và tính địa phương hóa cao của dữ liệu Việt Nam.

Sau đây là phần quan trọng nhất, đó là **hướng triển khai hiện tại và các mục tiêu nhóm đang theo đuổi**.

Về hệ thống phần mềm, nhóm đang triển khai backend FastAPI theo hướng có đầy đủ các nhóm chức năng cốt lõi. Mục tiêu là hệ thống sẽ có API dự đoán giá bất động sản, API thống kê dữ liệu, API quản lý danh sách bất động sản, API xem chi tiết từng hồ sơ, API quản lý nguồn dữ liệu, API ghi nhận audit log, API tải ảnh và API thu thập dữ liệu IoT từ điện thoại thông minh.

Về giao diện người dùng, nhóm đang xây dựng frontend React theo hướng có nhiều màn hình chức năng, bao gồm trang dự đoán giá, trang dashboard thống kê, trang thu thập dữ liệu bằng thiết bị di động, trang khám phá bản ghi, trang xem nguồn dữ liệu, trang dữ liệu tự thu thập và trang so sánh baseline.

Về dữ liệu, điều quan trọng mà nhóm muốn nhấn mạnh không phải là hiện đang có bao nhiêu bản ghi, mà là **nhóm lấy dữ liệu từ đâu và quản lý nguồn dữ liệu như thế nào**. Hiện tại, nhóm xác định hai lớp dữ liệu chính. Lớp thứ nhất là dữ liệu từ **nguồn công khai**, ví dụ như các website, các tin đăng bất động sản và các nguồn tham khảo thị trường mà nhóm có thể truy vết lại bằng tên nguồn, đường dẫn nguồn, thời điểm thu thập và trạng thái xác minh. Lớp thứ hai là dữ liệu **tự thu thập**, tức là dữ liệu do nhóm hoặc người dùng ghi nhận trực tiếp tại hiện trường thông qua biểu mẫu, quan sát thực địa, hình ảnh, vị trí GPS và các tín hiệu IoT lấy từ điện thoại thông minh.

Điểm mà nhóm hướng tới ở đây là mỗi bản ghi không chỉ có giá trị ở nội dung, mà còn có giá trị ở **nguồn gốc và độ tin cậy**. Đây là khác biệt quan trọng so với cách làm đơn thuần lấy một bảng dữ liệu rồi đưa ngay vào huấn luyện. Trong đề tài này, dữ liệu được nhìn nhận như một đối tượng cần được theo dõi nguồn, theo dõi trạng thái xác minh và theo dõi lịch sử thay đổi. Chính điều đó làm cho hệ thống có khả năng phát triển theo hướng thực tế hơn.

Nếu so sánh với các mô hình trong các bài báo khoa học mà nhóm tham khảo, có thể thấy một số khác biệt rõ ràng. Nhiều bài báo trên *Land*, *Journal of Real Estate Finance and Economics*, *Journal of Property Research* hay *PLOS ONE* thường tập trung mạnh vào phần tối ưu độ chính xác của mô hình trên một bộ dữ liệu đã được chuẩn hóa sẵn, tương đối sạch, và thường chỉ nghiên cứu sâu trên một thị trường hoặc một loại dữ liệu cụ thể. Một số nghiên cứu thiên về dữ liệu bảng, một số nghiên cứu thiên về ảnh, một số nghiên cứu nhấn mạnh giải thích mô hình hoặc lượng hóa bất định.

Trong khi đó, hướng tiếp cận của đồ án này khác ở chỗ nhóm không chỉ hỏi “mô hình nào dự đoán tốt hơn”, mà còn hỏi “một hệ thống dùng ngoài thực tế cần dữ liệu từ đâu, ai thu thập, xác minh thế nào, có thể bổ sung dữ liệu thực địa ra sao, và làm sao để người dùng tin vào kết quả dự đoán”. Nói cách khác, các bài báo khoa học thường nhấn mạnh chiều sâu mô hình, còn đồ án của nhóm cố gắng kết nối giữa **mô hình học máy, quy trình dữ liệu và khả năng triển khai thành hệ thống ứng dụng**.

Điểm khác biệt tiếp theo là về đặc trưng đầu vào. Phần lớn các mô hình trong các bài báo khoa học về bất động sản thường sử dụng các biến truyền thống như diện tích, vị trí, số phòng, loại tài sản, điều kiện kinh tế xã hội hoặc dữ liệu ảnh. Đồ án của nhóm vẫn kế thừa các đặc trưng cốt lõi đó, nhưng bổ sung thêm một hướng có tiềm năng là **dữ liệu IoT từ điện thoại thông minh** như mức độ ồn, GPS, điều kiện môi trường và ghi nhận tại hiện trường. Đây chưa phải là điểm mà tất cả các công trình đều làm, đặc biệt trong bối cảnh dữ liệu bất động sản tại Việt Nam còn phân tán và khó chuẩn hóa hoàn toàn.

Chính vì vậy, nếu nói về **điểm đột phá tiềm năng** của đề tài, nhóm cho rằng điểm đột phá không nằm ở việc khẳng định mình đã có mô hình tốt nhất, mà nằm ở chỗ đề tài đang mở ra một hướng tích hợp mới giữa dữ liệu thị trường và dữ liệu thực địa. Nếu tiếp tục hoàn thiện, hệ thống này có thể phát triển theo hướng đánh giá giá bất động sản gần với điều kiện sống thực tế hơn, thay vì chỉ dựa trên thông tin mô tả trong tin đăng.

Bên cạnh đó, nhóm cũng đang định hướng xây dựng nền tảng cho khả năng giải thích mô hình thông qua phần feature importance và hướng tích hợp SHAP. Điều này rất quan trọng vì trong lĩnh vực bất động sản, người dùng thường không chỉ quan tâm đến kết quả dự đoán, mà còn quan tâm đến việc mô hình dựa trên những yếu tố nào để đưa ra mức giá đó. Khi đặt cạnh các nghiên cứu quốc tế gần đây, đây cũng là một hướng đi phù hợp vì xu hướng hiện nay không chỉ dừng ở dự đoán, mà còn cần giải thích và minh bạch.

Tuy nhiên, để trình bày một cách trung thực và có trách nhiệm, nhóm cũng xin nêu rõ **những hạn chế hiện tại**.

Hạn chế thứ nhất là phần số liệu trong một số tài liệu báo cáo nội bộ và số liệu lưu trong hệ thống hiện vẫn chưa đồng bộ hoàn toàn. Cụ thể, có sự khác nhau giữa một số file báo cáo thực nghiệm và dữ liệu model version thực tế trong cơ sở dữ liệu. Nhóm xác định đây là một điểm cần được chuẩn hóa ngay để tránh sai lệch khi báo cáo học thuật.

Hạn chế thứ hai là giữa các phiên bản script và schema vẫn còn tồn tại một số tên trường chưa thật sự thống nhất, ví dụ như sự khác nhau giữa cách biểu diễn dữ liệu tự thu thập hoặc tên các trường GPS ở một số module. Điều này chưa làm hệ thống mất hoàn toàn chức năng, nhưng là một điểm kỹ thuật cần được xử lý để đảm bảo tính ổn định và minh bạch.

Hạn chế thứ ba là quy trình dữ liệu tự thu thập vẫn cần được chuẩn hóa chặt chẽ hơn ở mức học thuật, bao gồm quy trình chọn mẫu, tiêu chí xác minh và cách đưa dữ liệu đó vào huấn luyện sao cho vừa đúng yêu cầu học phần, vừa đảm bảo tính khách quan.

Hạn chế thứ tư là nhóm mới đang ở giai đoạn chứng minh tiềm năng của hướng tiếp cận, chứ chưa thể kết luận tuyệt đối về mức đóng góp của dữ liệu IoT. Muốn làm rõ điểm này, nhóm cần có thêm các thí nghiệm đối chứng, ví dụ như so sánh giữa mô hình có dùng IoT và mô hình không dùng IoT trên cùng một quy trình đánh giá.

Từ các hạn chế đó, nhóm xây dựng **phần đang cải tiến** như sau.

Thứ nhất, nhóm đang chuẩn hóa lại schema dữ liệu và quy ước đặt tên trường để toàn bộ pipeline từ thu thập dữ liệu, lưu database, huấn luyện mô hình, đánh giá và hiển thị kết quả được đồng nhất.

Thứ hai, nhóm đang thống nhất lại nguồn số liệu chính thức dùng để báo cáo, theo hướng lấy model version và kết quả đánh giá từ hệ thống làm nguồn chuẩn duy nhất.

Thứ ba, nhóm đang định hướng thực hiện đánh giá sâu hơn cho mô hình theo hướng so sánh có kiểm soát giữa các mô hình và giữa các bộ đặc trưng, trong đó đặc biệt quan tâm đến tác động thực sự của dữ liệu IoT.

Thứ tư, nhóm đang tiếp tục hoàn thiện phần giải thích mô hình và phần hiển thị mức độ tin cậy của dự đoán, để hệ thống không chỉ cho ra một con số giá, mà còn cho người dùng biết mức tin cậy tương đối và các yếu tố ảnh hưởng chính.

Thứ năm, nhóm dự kiến tiếp tục mở rộng dữ liệu tự thu thập theo hướng có quy trình xác minh rõ hơn, đồng thời điều chỉnh cách sampling sao cho vừa đạt yêu cầu học phần, vừa đảm bảo chất lượng huấn luyện.

Tiếp theo, về **giá trị mới, tiềm năng phát triển và ý nghĩa thực tiễn của đề tài**, nhóm cho rằng đồ án này có ba điểm nổi bật.

Thứ nhất, đề tài có tính thực tế vì xuất phát từ đúng nhu cầu ngoài đời: người mua cần mức giá tham khảo, người bán cần định vị tài sản, người môi giới cần công cụ hỗ trợ, và về lâu dài các đơn vị thẩm định hoặc ngân hàng cũng có thể tham khảo một hệ thống AVM ở mức hỗ trợ ra quyết định ban đầu.

Thứ hai, đề tài có tiềm năng vì không khóa mình trong một bộ dữ liệu tĩnh. Khi đã xây dựng được cấu trúc nguồn dữ liệu và quy trình thu thập, hệ thống có thể mở rộng thêm dữ liệu quy hoạch, dữ liệu giao thông, dữ liệu ảnh, hoặc dữ liệu cảm biến khác. Nghĩa là đồ án này không chỉ là một sản phẩm để nộp môn học, mà có thể trở thành một nền tảng kỹ thuật để phát triển tiếp.

Thứ ba, đề tài có sự khác biệt học thuật tương đối rõ so với nhiều bài báo chỉ dừng ở so sánh mô hình. Ở đây, nhóm đang cố gắng xây dựng một hướng kết hợp giữa dữ liệu công khai, dữ liệu thực địa, IoT smartphone, truy vết nguồn dữ liệu và khả năng giải thích mô hình. Vì vậy, giá trị của đồ án nằm ở chỗ nó đi gần hơn với một hệ thống thật có thể triển khai, chứ không chỉ là một thực nghiệm rời rạc trên dữ liệu mẫu.

Về **kế hoạch hoàn thiện trong giai đoạn tiếp theo**, nhóm dự kiến triển khai theo bốn hướng.

Hướng thứ nhất là hoàn thiện chất lượng dữ liệu và chuẩn hóa schema.

Hướng thứ hai là chạy lại thực nghiệm với cấu hình nhất quán, lưu đầy đủ artifact và đồng bộ báo cáo.

Hướng thứ ba là thực hiện các thí nghiệm đối chứng để làm rõ đóng góp của các nhóm đặc trưng, đặc biệt là đặc trưng IoT.

Hướng thứ tư là hoàn thiện báo cáo khoa học, phần trình bày học thuật và tài liệu chứng minh đối chiếu với các nghiên cứu tham khảo.

Cuối cùng, nhóm xin **kết luận** như sau.

Đề tài “Nghiên cứu và xây dựng hệ thống dự đoán giá bất động sản theo khu vực bằng học máy kết hợp dữ liệu IoT từ điện thoại thông minh” là một đề tài có ý nghĩa cả về mặt học thuật lẫn thực tiễn. Ở giai đoạn đề cương, nhóm tập trung xác định rõ kiến trúc hệ thống, nguồn dữ liệu, hướng mô hình hóa, cách so sánh học thuật và các mục tiêu kỹ thuật cần đạt tới. Đồng thời, nhóm cũng nhận diện rõ các hạn chế kỹ thuật và học thuật có thể phát sinh, từ đó đưa ra kế hoạch cải tiến cụ thể và có tính khả thi.

Nhóm rất mong nhận được ý kiến góp ý của thầy/cô hội đồng để tiếp tục hoàn thiện đề tài trong giai đoạn tiếp theo.

Nhóm xin chân thành cảm ơn thầy/cô đã lắng nghe.

---

## 2. Bài bảo vệ đề cương hoàn chỉnh khi hội đồng hỏi

### Câu hỏi 1: Vì sao nhóm chọn đề tài này?

Thưa thầy/cô, nhóm chọn đề tài này vì đây là bài toán có tính ứng dụng cao, gắn với nhu cầu thực tế của thị trường. Trong khi đó, định giá bất động sản hiện nay vẫn còn phụ thuộc nhiều vào kinh nghiệm chủ quan và thông tin phân tán từ nhiều nguồn. Nhóm muốn tiếp cận bài toán theo hướng công nghệ hơn, kết hợp học máy với dữ liệu thực địa để tăng tính khách quan, đồng thời xây dựng một hệ thống phần mềm hoàn chỉnh chứ không chỉ dừng ở mô hình lý thuyết.

### Câu hỏi 2: Điểm mới của đề tài nằm ở đâu?

Điểm mới của đề tài nằm ở chỗ nhóm không chỉ dùng dữ liệu bất động sản thông thường, mà còn kết hợp dữ liệu IoT từ điện thoại thông minh như độ ồn, GPS, nhiệt độ, độ ẩm và điều kiện môi trường tại thời điểm thu thập. Ngoài ra, nhóm còn chú trọng phần truy vết nguồn dữ liệu, trạng thái xác minh và audit log. Vì vậy, điểm mới không chỉ nằm ở mô hình mà còn ở cách thiết kế hệ thống và quy trình dữ liệu.

### Câu hỏi 3: Tại sao dữ liệu IoT lại có ý nghĩa với bài toán giá bất động sản?

Thưa thầy/cô, trong thực tế, giá trị bất động sản không chỉ phụ thuộc vào diện tích hay vị trí hành chính, mà còn phụ thuộc vào chất lượng môi trường sống. Ví dụ, một khu vực quá ồn, mật độ giao thông cao hoặc điều kiện hiện trường không thuận lợi có thể ảnh hưởng trực tiếp đến giá trị cảm nhận của người mua. Dữ liệu IoT từ điện thoại thông minh giúp nhóm có thêm một lớp thông tin thực địa mà các tin đăng thông thường không phản ánh đầy đủ.

### Câu hỏi bổ sung: Mô hình kiến trúc của hệ thống được tổ chức như thế nào?

Thưa thầy/cô, hệ thống của nhóm được thiết kế theo kiến trúc ba lớp. Lớp thứ nhất là lớp dữ liệu, nơi lưu thông tin bất động sản, nguồn dữ liệu, trạng thái xác minh, dữ liệu IoT, lịch sử dự đoán và version mô hình. Lớp thứ hai là lớp xử lý nghiệp vụ và trí tuệ nhân tạo, gồm backend FastAPI và pipeline học máy để tiền xử lý, huấn luyện, dự đoán và giải thích mô hình. Lớp thứ ba là lớp giao diện React để người dùng nhập thông tin, xem dashboard, kiểm tra nguồn dữ liệu và nhận kết quả dự đoán. Kiến trúc này phù hợp vì dễ mở rộng, dễ bảo trì và gần với một hệ thống thực tế hơn là một mô hình chạy rời rạc.

### Câu hỏi bổ sung: Nhóm sử dụng những thuật toán nào và dùng để làm gì?

Thưa thầy/cô, nhóm sử dụng ba mô hình hồi quy chính là RandomForest, GradientBoosting và XGBoost. RandomForest được dùng như mô hình baseline mạnh và ổn định trên dữ liệu bảng. GradientBoosting được dùng để tối ưu sai số theo hướng học tăng cường tuần tự và là mô hình nhóm ưu tiên theo định hướng kỹ thuật. XGBoost được dùng như một lựa chọn boosting nâng cao để so sánh thêm với hai mô hình còn lại. Ngoài ra, hệ thống còn dùng cross-validation để đánh giá mô hình, one-hot encoding và target encoding để xử lý đặc trưng, Haversine để tính khoảng cách vị trí, và SHAP để giải thích kết quả dự đoán.

### Câu hỏi bổ sung: Nhóm có train LLM không, và dữ liệu được train như thế nào?

Thưa thầy/cô, nếu dùng đúng thuật ngữ kỹ thuật thì đồ án này hiện không fine-tune hay train LLM theo nghĩa mô hình ngôn ngữ lớn. Đồ án đang train các mô hình học máy hồi quy trên dữ liệu bất động sản có cấu trúc. Dữ liệu được lấy từ cơ sở dữ liệu của hệ thống, lọc theo điều kiện phù hợp, đưa qua bước tiền xử lý và feature engineering, sau đó chia train-test để huấn luyện các mô hình như RandomForest, GradientBoosting và XGBoost. Sau khi đánh giá bằng MAE, RMSE và R bình phương, nhóm chọn mô hình phù hợp hơn để lưu version và triển khai dự đoán.

### Câu hỏi bổ sung: Khi train mô hình, nhóm gặp vấn đề gì và xử lý như thế nào?

Thưa thầy/cô, khó khăn lớn nhất là dữ liệu bất động sản không đồng nhất, có nhiều trường bị thiếu và chênh lệch mạnh theo khu vực. Nhóm xử lý bằng cách chuẩn hóa schema, lọc dữ liệu theo trạng thái xác minh, xây dựng bước tiền xử lý cho biến thiếu và biến phân loại, tạo thêm đặc trưng vị trí và IoT, đồng thời huấn luyện nhiều mô hình để so sánh thay vì phụ thuộc vào một mô hình duy nhất. Về dài hạn, nhóm tiếp tục làm thực nghiệm đối chứng để đo rõ hơn mức đóng góp của từng nhóm đặc trưng.

### Câu hỏi bổ sung: Đề tài khác gì so với các đề tài và bài báo tham khảo, và vì sao lại phù hợp với Việt Nam?

Thưa thầy/cô, nhiều bài báo tham khảo tập trung vào việc tối ưu độ chính xác của mô hình trên bộ dữ liệu đã được chuẩn hóa tốt. Trong khi đó, đề tài của nhóm khác ở chỗ nhóm xây dựng cả một hệ thống có truy vết nguồn dữ liệu, có xác minh, có dữ liệu thực địa và có khả năng tích hợp IoT smartphone. Điểm này phù hợp với Việt Nam vì dữ liệu bất động sản trong nước thường phân tán, không đồng nhất và khác biệt rất mạnh theo khu vực. Do đó, một mô hình chỉ học trên dữ liệu bảng thuần túy sẽ chưa đủ, còn hướng tiếp cận của nhóm cho phép kết hợp thông tin thị trường với đặc trưng địa phương và điều kiện thực tế tại hiện trường.

### Câu hỏi 4: Kết quả hiện tại của nhóm đã đủ thuyết phục chưa?

Thưa thầy/cô, ở giai đoạn đề cương, nhóm chưa xem bất kỳ kết quả nào là kết luận cuối cùng. Điều mà nhóm muốn chứng minh trước hết là hướng tiếp cận này có cơ sở kỹ thuật, có cơ sở học thuật và có tính khả thi để tiếp tục triển khai. Tuy nhiên, nhóm cũng thẳng thắn nhìn nhận rằng để bảo vệ chặt chẽ hơn thì vẫn cần thêm các thí nghiệm đối chứng để làm rõ đóng góp của từng nhóm đặc trưng, đặc biệt là đặc trưng IoT.

### Câu hỏi 5: Nhóm đã làm được những gì, và phần nào mới chỉ đang đề xuất?

Phần đã làm được gồm có cơ sở dữ liệu, backend FastAPI, frontend React, pipeline huấn luyện mô hình, lưu version mô hình, dashboard thống kê, quản lý nguồn dữ liệu, quản lý bản ghi, và nền tảng thu thập IoT. Phần đang tiếp tục hoàn thiện là chuẩn hóa schema giữa các module, đồng bộ báo cáo thực nghiệm với số liệu trong hệ thống, lượng hóa rõ hơn tác động của IoT bằng thực nghiệm ablation, và tăng cường phần giải thích mô hình.

### Câu hỏi 6: Nguồn dữ liệu của nhóm lấy từ đâu và vì sao cách lấy đó có ý nghĩa?

Thưa thầy/cô, nhóm đi theo hai hướng. Hướng thứ nhất là lấy dữ liệu từ các nguồn công khai như website và tin đăng bất động sản, nhưng không dùng theo kiểu sao chép rời rạc mà gắn với thông tin nguồn, liên kết, thời điểm thu thập và trạng thái xác minh. Hướng thứ hai là dữ liệu tự thu thập tại hiện trường thông qua biểu mẫu, quan sát, hình ảnh, GPS và dữ liệu IoT từ điện thoại thông minh. Ý nghĩa của cách làm này là hệ thống không chỉ học từ dữ liệu thị trường, mà còn có khả năng gắn thêm tín hiệu thực địa để tiến gần hơn với điều kiện sử dụng thật.

### Câu hỏi 7: Nếu hội đồng hỏi tài liệu tham khảo của nhóm có đủ chuẩn khoa học không thì trả lời thế nào?

Thưa thầy/cô, nhóm sử dụng hai lớp tài liệu tham khảo. Lớp thứ nhất là sách học thuật của Springer có ISBN rõ ràng để làm nền tảng lý thuyết. Lớp thứ hai là các bài báo trên các tạp chí và nhà xuất bản quốc tế như *Land*, *Sensors*, *PLOS ONE*, *Journal of Real Estate Finance and Economics* và *Journal of Property Research*. Các tài liệu này đều có DOI chính thức, và nhóm sử dụng để đối chiếu phương pháp, hướng đánh giá và ý nghĩa ứng dụng của đề tài.

### Câu hỏi 8: Vì sao nhóm cho rằng đồ án này có tính thực tế chứ không chỉ là mô hình nghiên cứu?

Thưa thầy/cô, nhóm cho rằng tính thực tế của đồ án nằm ở ba điểm. Một là dữ liệu được tổ chức theo nguồn gốc rõ ràng, nên có thể dùng trong quy trình vận hành thật thay vì chỉ để huấn luyện một lần. Hai là hệ thống có backend, frontend, dashboard, quản lý bản ghi và khả năng mở rộng, nên đây là một sản phẩm phần mềm chứ không chỉ là file notebook. Ba là dữ liệu IoT và dữ liệu thực địa giúp hệ thống tiến gần hơn với bối cảnh ngoài đời, nơi người dùng quan tâm không chỉ đến thông tin trong tin đăng mà còn quan tâm đến chất lượng môi trường và điều kiện khu vực.

### Câu hỏi 9: Tại sao nhóm chọn GradientBoosting thay vì RandomForest hoặc XGBoost?

Theo định hướng thử nghiệm hiện tại, GradientBoosting là mô hình mà nhóm ưu tiên xem xét hơn so với RandomForest trong bài toán này. Tuy nhiên, nhóm chưa coi đó là kết luận tuyệt đối, vì khi dữ liệu thay đổi hoặc khi đặc trưng được cải tiến thêm thì lựa chọn tối ưu cũng có thể thay đổi. Do đó, nhóm sẽ tiếp tục đánh giá bằng thực nghiệm có kiểm soát thay vì kết luận chỉ dựa trên một lần chạy.

### Câu hỏi 10: Hướng phát triển xa hơn của đề tài là gì?

Trong giai đoạn tiếp theo, nhóm muốn mở rộng theo ba hướng. Thứ nhất là nâng cao chất lượng dữ liệu và mức độ xác minh thực địa. Thứ hai là bổ sung đánh giá độ bất định và giải thích mô hình ở mức từng dự đoán. Thứ ba là hướng tới khả năng triển khai trên dữ liệu lớn hơn, thậm chí kết hợp thêm dữ liệu ảnh, dữ liệu quy hoạch hoặc dữ liệu giao thông để tăng chất lượng định giá.

---

## 3. Đoạn kết khi muốn chốt buổi bảo vệ thật gọn

Kính thưa thầy/cô, qua phần trình bày và bảo vệ đề cương, nhóm mong muốn làm rõ rằng đề tài của nhóm không chỉ là một mô hình dự đoán giá đơn giản, mà là một hướng xây dựng hệ thống AVM có kết hợp dữ liệu thực địa và có định hướng học thuật rõ ràng. Nhóm đã xác định được nền tảng kiến trúc, hướng dữ liệu, hướng mô hình và các mục tiêu kỹ thuật cần đạt tới, đồng thời cũng ý thức rất rõ những điểm còn hạn chế để tiếp tục cải tiến. Nhóm rất mong nhận được góp ý của thầy/cô để hoàn thiện đề tài một cách chặt chẽ hơn trong thời gian tới.

Nhóm xin chân thành cảm ơn.
