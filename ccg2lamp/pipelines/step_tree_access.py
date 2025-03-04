from typing import List
import logging
import copy

from lxml import etree
from ccg2lamp.scripts.theorem import generate_semantics_from_doc
from ccg2lamp.scripts.semantic_types import get_dynamic_library_from_doc

from ccg2lamp.pipelines.data_types import EntailProof, CorpusSemantics, DocumentSemantics

#===================================================
# Tree utilities to support custom steps
#===================================================


class CCGTree():
    """access and transform semantic data in the XML tree"""
    def __init__(self, root: etree._Element,
                 use_gold_trees: bool = False,
                 max_sentences: int = 100,
                 min_sentences: int = 1):
        assert root is not None
        self.ccg_tree = root
        self.max_sentences = max_sentences
        self.min_sentences = min_sentences
        self.use_gold_trees = use_gold_trees
    
    def __add__(self, ccg_tree):
        """merge another CCGTree into this one such that we
        can arbitrarily combine two parsed corpora into one
        to derive the composite context without reparsing 
        the sentences
        """
        if ccg_tree is None or ccg_tree is self:
            return self

        # copy-on-write the tree, so it can be rejoined
        merged_tree = copy.deepcopy(self.ccg_tree)
        merged_sentences = merged_tree.xpath('//sentences')[0]
        source_sentences = ccg_tree.ccg_tree.xpath('//sentences')[0]
        for sent_node in source_sentences.getiterator("sentence"):
            merged_sentences.append(sent_node)
        
        merged_ccg = CCGTree(merged_tree,
                             use_gold_trees=self.use_gold_trees,
                             max_sentences=self.max_sentences,
                             min_sentences=self.min_sentences)
        return merged_ccg       
    
    def get_entail_proof(self, doc_element: etree._Element) -> object:
        """retrieve entailment proof of the document, if any"""
        # a document has at most one inference derived 
        # from many interpretations of its corpus
        entail_proof = None
        for proof_element in doc_element.getiterator("proof"):
            entail_proof = EntailProof(status=proof_element.get("status"),
                                       inference_result=proof_element.get("inference_result"),
                                       proof_node=proof_element)
        return entail_proof

    def get_doc_semantics(self, doc_element: etree._Element) -> List[CorpusSemantics]:
        """retrieve the semantic data for a collection of sentences of a document"""
        corpus_semantics = []

        # generate all possible interpretations of the corpus
        # sem_product = [semantics(s1) x ... x semantics(sn)]
        # where semantics(si) = [<semantics>{1, n_best}] for sentence si
        sem_product = generate_semantics_from_doc(doc_element, 
                                                  max_gen=self.max_sentences, 
                                                  use_gold_trees=self.use_gold_trees, 
                                                  min_sentences=self.min_sentences)
        # collect all interpretations of the corpus
        for sent_semantics in sem_product:
            dynamic_library_str, sent_formulas = get_dynamic_library_from_doc(doc_element, 
                                                                              sent_semantics)
            # one interpretation of the corpus
            result = CorpusSemantics(dynamic_library=dynamic_library_str,
                                     semantic_nodes=sent_semantics,
                                     logic_formulas=sent_formulas)
            corpus_semantics.append(result)
            
        return corpus_semantics
        
    def get_semantics(self) -> List[DocumentSemantics]:
        """retrieve the semantic data of each document"""
        doc_elements = self.ccg_tree.findall('.//document')
        doc_semantics = []
        for doc_node in doc_elements:
            doc_sem = self.get_doc_semantics(doc_node)
            doc_infer = self.get_entail_proof(doc_node)
            result = DocumentSemantics(doc_node=doc_node, 
                                       doc_sem=doc_sem, 
                                       doc_infer=doc_infer)
            doc_semantics.append(result)
        return doc_semantics
        
# unit test
if __name__ == "__main__":
    from ccg2lamp.pipelines.step_tree_io import CCGTreeReader, CCGTreeWriter
    logging.basicConfig(level=logging.DEBUG)

    data_1 = CCGTreeReader().transform("datasets/corpus_test/sentences.sem.1.xml")
    data_2 = CCGTreeReader().transform("datasets/corpus_test/sentences.sem.2.xml")
    data_3 = CCGTreeReader().transform("datasets/corpus_test/sentences.sem.3.xml")

    # test + operator
    # write the merged tree back to check it has been reconstructed
    m_tree = sum([CCGTree(data_2.parse_result), CCGTree(data_3.parse_result)], CCGTree(data_1.parse_result))
    tree_writer = CCGTreeWriter(output_suffix="sem.xml")
    data_3.parse_result = m_tree.ccg_tree
    tree_writer.transform(data_3)
    
    # test access functions
    data = CCGTreeReader().transform("datasets/corpus_test/sentences.pro.xml")
    tree_sems = CCGTree(data.parse_result).get_semantics()
    print(tree_sems)

    
